"""Проверка и сборка пачки примеров.

  python3 /home/claude/ds/tools/build.py BATCH.py --dry          # запустить код, показать реальный вывод
  python3 /home/claude/ds/tools/build.py BATCH.py --out PART.jsonl # проверить и дописать в PART.jsonl

BATCH.py определяет EXAMPLES = [dict(id=..., category=..., kind=..., lang=..., question=..., code=..., answer=...), ...]
Необязательно: stdin="...", fence=False (код без ```), run=False (не запускать: недетерминированный код).
"""
from __future__ import annotations

import difflib
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from runner import run_code  # noqa: E402
from eval_set import EVAL  # noqa: E402
from dedup import Index  # noqa: E402

KINDS = {"gotcha", "explain", "bug", "output", "system", "compare", "write"}
LANGS = {"python", "javascript", "c", "cpp", "java", "sql", "none"}
FENCE = {"python": "python", "javascript": "javascript", "c": "c", "cpp": "cpp", "java": "java", "sql": "sql", "none": ""}
FILLER = ["давайте разбер", "таким образом", "надеюсь, это", "в заключение", "давайте рассмотр"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


EVAL_CODES = [norm(e["code"]) for e in EVAL]


def load(batch: Path):
    spec = importlib.util.spec_from_file_location("batch_mod", batch)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.EXAMPLES


def cyr_ratio(text: str) -> float:
    prose = re.sub(r"```.*?```", " ", text, flags=re.S)
    prose = re.sub(r"`[^`]*`", " ", prose)
    letters = [c for c in prose if c.isalpha()]
    if not letters:
        return 0.0
    return sum("а" <= c.lower() <= "я" or c.lower() == "ё" for c in letters) / len(letters)


def user_message(ex) -> str:
    if ex["kind"] == "write":
        # задача «напиши»: код — это решение в ответе, в вопросе его нет (кроме необязательного context)
        ctx = ex.get("context", "").strip()
        return ex["question"].strip() + (f"\n\n{ctx}" if ctx else "")
    q, code = ex["question"].strip(), ex["code"].rstrip()
    block = code if ex.get("fence") is False else f"```{FENCE.get(ex['lang'], '')}\n{code}\n```"
    if "{code}" in q:
        return q.replace("{code}", block)
    return f"{q}\n\n{block}"


def check(ex, observed, seen_ids, index=None):
    errs, warns = [], []
    for k in ("id", "category", "kind", "lang", "question", "code", "answer"):
        if not str(ex.get(k, "")).strip():
            errs.append(f"нет поля {k}")
    if errs:
        return errs, warns
    if ex["id"] in seen_ids:
        errs.append("повтор id")
    if ex["kind"] not in KINDS:
        errs.append(f"kind должен быть из {sorted(KINDS)}")
    if ex["lang"] not in LANGS:
        errs.append(f"lang должен быть из {sorted(LANGS)}")
    a = ex["answer"]
    words = len(a.split())
    lim = 900 if ex["kind"] == "system" else 600
    if words < 50 or words > lim:
        errs.append(f"длина ответа {words} слов (нужно 50..{lim})")
    if cyr_ratio(a) < 0.6:
        errs.append("ответ не на русском (мало кириллицы вне кода)")
    if ex["kind"] == "write" and norm(ex["code"]) not in norm(a):
        errs.append("kind=write: проверяемый code должен целиком входить в ответ (в блоке ```)")
    if ex.get("run") is False and ex["lang"] == "python":
        try:
            compile(ex["code"], "<code>", "exec")
        except SyntaxError as e:
            errs.append(f"run=False, но код не компилируется: {e}")
    if index is not None and ex["code"].strip():
        twin = index.find(ex["lang"], ex["code"])
        if twin:
            errs.append(f"дубликат {twin}: тот же код с другими именами — нужна другая ситуация "
                        "или другой механизм")
    nc = norm(ex["code"])
    for ec in EVAL_CODES:
        if difflib.SequenceMatcher(None, nc, ec).ratio() > 0.8:
            errs.append("код слишком похож на пример из контрольного набора — поменяйте")
    if observed is not None:
        if observed.startswith("[compile error]"):
            if ex["kind"] != "bug":
                errs.append(f"код не компилируется: {observed}")
        m = re.search(r"\[stderr\] ([A-Za-z_][\w.]*(?:Error|Exception|Interrupt|Exit))", observed)
        if m:
            name = m.group(1).split(".")[-1]
            if name not in a:
                errs.append(f"код падает с {name}, но в ответе это не названо")
        if "TIMEOUT" in observed:
            errs.append("код завис (таймаут) — сделайте детерминированным/быстрым или run=False")
        if ex["kind"] == "output" and ex["lang"] != "sql":
            lines = [l.strip() for l in observed.splitlines() if l.strip() and not l.startswith("[stderr]")]
            if 0 < len(lines) <= 6:
                squash = lambda t: re.sub(r"\s+", "", t).lower()
                na = squash(a)
                missing = [l for l in lines if len(l) <= 100 and squash(l) not in na]
                if missing:
                    errs.append(f"kind=output: в ответе нет реального вывода: {missing}")
    for f in FILLER:
        if f in a.lower():
            warns.append(f"вода: «{f}…»")
    return errs, warns


def process(exs, out: Path | None, dry: bool = False, partial: bool = False, label=lambda ex: ex.get("id")):
    """Проверяет примеры и дописывает годные в out.

    partial=False — всё или ничего (для своих пачек); partial=True — годные пишутся,
    плохие возвращаются списком (удобно для ответов ChatGPT: исправлять только плохие).
    Возвращает (записано, [(пример, ошибки, реальный вывод), ...]).
    """
    seen = set()
    if out and out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                seen.add(json.loads(line)["id"])
    good, bad = [], []
    index = None if dry else Index.from_parts()
    for ex in exs:
        observed = None if ex.get("run") is False else run_code(ex.get("lang", "none"), ex.get("code", ""), ex.get("stdin"))
        if dry:
            print(f"=== {label(ex)} [{ex.get('lang')}] ===\n{observed}\n")
            continue
        errs, warns = check(ex, observed, seen, index)
        for w in warns:
            print(f"  ! {label(ex)}: {w}")
        if errs:
            bad.append((ex, errs, observed))
            print(f"✗ {label(ex)}: " + "; ".join(errs))
            print(f"    реальный вывод: {observed!r}")
            continue
        seen.add(ex["id"])
        index.add(ex["id"], ex["lang"], ex["code"])       # повтор внутри той же пачки — тоже дубль
        good.append({
            "id": ex["id"], "category": ex["category"], "kind": ex["kind"], "lang": ex["lang"],
            "observed_output": observed, "code": ex["code"], "stdin": ex.get("stdin"),
            "messages": [{"role": "user", "content": user_message(ex)},
                         {"role": "assistant", "content": ex["answer"].strip()}],
        })
    if dry:
        return 0, bad
    if bad and not partial:
        print(f"\n{len(bad)} примеров с ошибками — пачка НЕ записана. Исправьте и запустите снова.")
        return 0, bad
    if good:
        with out.open("a", encoding="utf-8") as f:
            for g in good:
                f.write(json.dumps(g, ensure_ascii=False) + "\n")
    total = sum(1 for l in out.read_text().splitlines() if l.strip()) if out.exists() else 0
    print(f"✓ записано {len(good)} примеров, всего в {out.name}: {total}")
    return len(good), bad


def main():
    batch = Path(sys.argv[1])
    dry = "--dry" in sys.argv
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    _written, bad = process(load(batch), out, dry=dry)
    if bad and not dry:
        sys.exit(1)


if __name__ == "__main__":
    main()
