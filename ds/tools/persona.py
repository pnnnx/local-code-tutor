"""Режим «ворчун»: реакции с характером перед уже проверенными объяснениями.

  ./ds.sh persona        пошагово, как ./ds.sh go: промпт в буфер -> ответ ChatGPT -> Enter
  ./ds.sh persona add F  проверить сохранённый ответ из файла

ChatGPT пишет ТОЛЬКО реакции (1-2 фразы) и короткие повторные объяснения для диалогов
«опять не понял»; основное объяснение берётся из датасета (оно уже проверено запуском).
Строки пишутся в parts/persona.jsonl с системной строкой режима — без неё модель
должна отвечать как обычно, поэтому исходные примеры остаются в датасете тоже.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402
import coverage  # noqa: E402
import gpt  # noqa: E402
import gitlog  # noqa: E402

DATA = json.loads((HERE / "persona_data.json").read_text(encoding="utf-8"))
PERSONA = DATA["persona"]
OUT = ROOT / "parts" / "persona.jsonl"
STYLE_FILE = ROOT / "persona_style.txt"
KINDS = ("bug", "gotcha", "output", "explain", "compare")
N_REACT, N_AGAIN = 16, 4
ROUNDS_PER_CHAT = 4


# ---------------------------------------------------------------- выбор примеров
def _h(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def pool(rows):
    """Ещё не использованные исходные примеры, вперемешку по категориям."""
    used = {r.get("base_id") for r in rows if r.get("persona")}
    by_cat = defaultdict(list)
    for r in rows:
        if r.get("persona") or r["id"] in used or r["kind"] not in KINDS:
            continue
        if len(r["messages"]) != 2:
            continue
        by_cat[r["category"]].append(r)
    for c in by_cat:
        by_cat[c].sort(key=lambda r: _h(r["id"]))
    out, cats = [], sorted(by_cat, key=_h)
    while any(by_cat.values()):
        for c in cats:
            if by_cat[c]:
                out.append(by_cat[c].pop())
    return out


def gist(answer: str) -> str:
    first = re.split(r"\n\s*\n", answer.strip(), maxsplit=1)[0]
    mech = coverage.MECH_RE.search(answer)
    text = re.sub(r"\s+", " ", first)[:260]
    return text + (f" [механизм: {mech.group(1).strip()}]" if mech else "")


def item_text(r) -> str:
    q = r["messages"][0]["content"].strip()
    if len(q) > 900:
        q = q[:900] + "\n…(обрезано)"
    return f"### {r['id']}\n{q}\nСуть готового объяснения: {gist(r['messages'][1]['content'])}"


def style_text() -> str:
    if not STYLE_FILE.exists():
        return ""
    lines = [l.strip() for l in STYLE_FILE.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
    return (DATA["style_header"] + "\n".join(f"- {l}" for l in lines) + "\n") if lines else ""


def make_prompt(first: bool):
    rows = coverage.load()
    cand = pool(rows)
    if not cand:
        raise SystemExit("Все подходящие примеры уже с реакциями. Соберите ещё примеров (./ds.sh).")
    react, again = cand[:N_REACT], cand[N_REACT:N_REACT + N_AGAIN]
    items = ("REACT:\n\n" + "\n\n".join(item_text(r) for r in react)
             + ("\n\nAGAIN:\n\n" + "\n\n".join(item_text(r) for r in again) if again else ""))
    tpl = DATA["prompt"] if first else DATA["more"]
    return tpl.format(style=style_text(), items=items)


# ---------------------------------------------------------------- проверка и запись
def words(s: str) -> int:
    return len(s.split())


class Checker:
    def __init__(self, rows):
        self.seen = [r["reaction"] for r in rows if r.get("persona") and r.get("reaction")]
        self.starts = Counter(self._start(s) for s in self.seen)

    @staticmethod
    def _start(s: str) -> str:
        return " ".join(re.findall(r"\w+", s.lower())[:3])

    def reaction(self, s) -> str | None:
        if not isinstance(s, str) or not s.strip():
            return "пусто"
        s = s.strip()
        if "```" in s:
            return "в реакции не нужен код"
        if not 4 <= words(s) <= 45:
            return f"{words(s)} слов (нужно 4..45)"
        if build.cyr_ratio(s) < 0.6:
            return "не по-русски"
        low = s.lower()
        for old in self.seen:
            if difflib.SequenceMatcher(None, low, old.lower()).ratio() > 0.75:
                return f"почти повтор: «{old[:60]}»"
        if self.starts[self._start(s)] >= 3:
            return f"начало «{self._start(s)}» уже было 3 раза"
        return None

    def accept(self, s: str) -> None:
        self.seen.append(s.strip())
        self.starts[self._start(s)] += 1


def parse(text: str):
    i = text.find("REACTIONS")
    j = text.find("AGAIN")
    starts = [k for k in (i, j) if k >= 0]
    if not starts:
        return None
    body = re.sub(r"\n?[`~]{3,}\s*$", "", text[min(starts):].rstrip())
    ns = {}
    try:
        exec(compile(body, "<chatgpt>", "exec"), {"dict": dict}, ns)
    except SyntaxError:
        return "broken"
    return ns.get("REACTIONS") or {}, ns.get("AGAIN") or {}


def add(text: str) -> int:
    parsed = parse(text)
    if parsed is None:
        print("   ⚠ В ответе нет REACTIONS / AGAIN.")
        return 0
    if parsed == "broken":
        print("   ⚠ Скопирован не весь ответ. Нажмите Copy у большого блока в конце ответа ChatGPT.")
        return 0
    reactions, again = parsed
    rows = coverage.load()
    base = {r["id"]: r for r in rows if not r.get("persona")}
    done = {r.get("base_id") for r in rows if r.get("persona")}
    chk = Checker(rows)
    new, bad = [], []

    def head(bid):
        r = base.get(bid)
        if r is None:
            return None, "нет такого id"
        if bid in done:
            return None, "уже есть"
        return r, None

    for bid, s in reactions.items():
        r, err = head(bid)
        err = err or chk.reaction(s)
        if err:
            bad.append((bid, err))
            continue
        chk.accept(s)
        done.add(bid)
        new.append(row(r, "persona", s.strip(), [
            {"role": "user", "content": r["messages"][0]["content"]},
            {"role": "assistant", "content": s.strip() + "\n\n" + r["messages"][1]["content"]}]))
    for bid, d in again.items():
        r, err = head(bid)
        if not err and not isinstance(d, dict):
            err = "нужен dict(first=..., user=..., answer=...)"
        if not err:
            err = chk.reaction(d.get("first"))
        if not err:
            u, a = str(d.get("user", "")).strip(), str(d.get("answer", "")).strip()
            if not 2 <= words(u) <= 40:
                err = f"user: {words(u)} слов (нужно 2..40)"
            elif not 30 <= words(a) <= 220:
                err = f"answer: {words(a)} слов (нужно 30..220)"
            elif build.cyr_ratio(a) < 0.6:
                err = "answer не по-русски"
        if err:
            bad.append((bid, err))
            continue
        first = d["first"].strip()
        chk.accept(first)
        done.add(bid)
        new.append(row(r, "again", first, [
            {"role": "user", "content": r["messages"][0]["content"]},
            {"role": "assistant", "content": first + "\n\n" + r["messages"][1]["content"]},
            {"role": "user", "content": d["user"].strip()},
            {"role": "assistant", "content": d["answer"].strip()}]))
    for bid, err in bad:
        print(f"   ✗ {bid}: {err}")
    if new:
        with OUT.open("a", encoding="utf-8") as f:
            for n in new:
                f.write(json.dumps(n, ensure_ascii=False) + "\n")
    total = sum(1 for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()) if OUT.exists() else 0
    print(f"✓ принято {len(new)} из {len(reactions) + len(again)} · всего в режиме «ворчун»: {total}"
          f" (цель {coverage.TARGETS.get('persona', 300)})")
    if new:
        rej = "\n".join(f"- {b}: {e}" for b, e in bad) or "- нет"
        gitlog.commit([OUT], f"ds: +{len(new)} ворчун (всего {total})",
                      f"Принято {len(new)} из {len(reactions) + len(again)} реакций/диалогов «ворчуна»; "
                      f"`ds/parts/persona.jsonl`: {total}.",
                      "`./ds.sh persona` → ChatGPT пишет реакции → отсев (длина, русский, повторы) → "
                      "склейка с проверенным объяснением.",
                      f"Режим «ворчун» (DECISIONS #7): {total} из 300.",
                      "Отклонено:\n" + rej)
    return len(new)


def row(base_row, prefix, reaction, msgs):
    return {"id": f"{prefix}-{base_row['id']}", "category": "persona", "kind": base_row["kind"],
            "lang": base_row["lang"], "persona": True, "base_id": base_row["id"], "reaction": reaction,
            "observed_output": None,
            "messages": [{"role": "system", "content": PERSONA}] + msgs}


# ---------------------------------------------------------------- пошаговый режим
def go() -> None:
    gpt.deliver(make_prompt(first=True), "Промпт «ворчун» для нового чата")
    print("\n① Откройте НОВЫЙ чат ChatGPT → Cmd+V → отправьте.")
    last, rounds = gpt.from_clipboard(), 0
    while True:
        print("② Когда ChatGPT ответит — Copy на блоке кода и вернитесь сюда.")
        if gpt.ask("   Enter — проверить ответ · q — выход › ") in ("q", "й", "exit", "выход"):
            print("Готово. Итоговый файл для обучения: ./ds.sh build")
            return
        raw = gpt.from_clipboard()
        if raw == last:
            print("   ⚠ Буфер не изменился — нажмите Copy именно на ответе ChatGPT.\n")
            continue
        last = raw
        if add(raw) == 0 and parse(raw) in (None, "broken"):
            continue
        save_raw(raw)
        rounds += 1
        if rounds >= ROUNDS_PER_CHAT:
            rounds = 0
            gpt.deliver(make_prompt(first=True), "Промпт для НОВОГО чата")
            print("③ Чат длинный — дальше шутки начнут повторяться. Откройте НОВЫЙ чат → Cmd+V.\n")
        else:
            gpt.deliver(make_prompt(first=False), "Следующая порция")
            print("③ Вставьте в ТОТ ЖЕ чат (Cmd+V).\n")
        last = gpt.from_clipboard()


def save_raw(text: str) -> None:
    d = ROOT / "batches"
    d.mkdir(exist_ok=True)
    n = 1
    while (d / f"persona_{n:02d}.py").exists():
        n += 1
    (d / f"persona_{n:02d}.py").write_text(text, encoding="utf-8")


def main(argv):
    if argv[:1] == ["add"] and len(argv) > 1:
        add(Path(argv[1]).read_text(encoding="utf-8"))
    elif argv[:1] == ["prompt"]:
        print(make_prompt(first=True))
    else:
        go()


if __name__ == "__main__":
    main(sys.argv[1:])
