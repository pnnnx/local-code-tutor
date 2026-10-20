"""Сборка финального датасета: повторный прогон кода, дедуп, статистика, запись train-файла."""
import difflib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from runner import run_code  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CODE_RE = re.compile(r"```(\w*)\n(.*?)```", re.S)


def user_code(msg):
    m = CODE_RE.search(msg)
    return m.group(2) if m else msg


def main(rerun=True):
    rows = []
    for p in sorted((ROOT / "parts").glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    print("всего строк:", len(rows))

    # 1) повторный прогон: вывод должен совпасть с записанным
    mismatch, unchecked = [], Counter()
    if rerun:
        import shutil
        from runner import missing_modules
        tools = {"javascript": "node", "c": "gcc", "cpp": "g++", "java": "javac"}
        absent = {lang for lang, exe in tools.items() if not shutil.which(exe)}
        mod_cache: dict = {}
        for r in rows:
            if r["observed_output"] is None:
                continue
            code = r.get("code") or user_code(r["messages"][0]["content"])
            # на этой машине нечем проверить — не выбрасываем: пример уже проверен при добавлении
            if r["lang"] in absent:
                unchecked[f"нет {tools[r['lang']]}"] += 1
                continue
            if r["lang"] == "python":
                mods = set(re.findall(r"^\s*(?:import|from)\s+(\w+)", code, re.M))
                miss = [m for m in mods if mod_cache.setdefault(m, bool(missing_modules({m})))]
                if miss:
                    unchecked[f"нет модуля {','.join(sorted(miss))}"] += 1
                    continue
            again = run_code(r["lang"], code, r.get("stdin"))
            if (again or "").strip() != (r["observed_output"] or "").strip():
                mismatch.append(r["id"])
        print("несовпадений при повторном запуске:", len(mismatch), mismatch[:20])
        if unchecked:
            print("не перепроверено (нечем запустить здесь, проверены при добавлении):", dict(unchecked))

    # 2) дубликаты по «скелету» кода (имена/строки/числа обезличены) — по всему датасету
    from dedup import Index, row_code
    index, dups = Index(), set()
    for r in rows:
        if r.get("persona"):        # «ворчун» повторяет код исходного примера — это не дубль
            continue
        twin = index.find(r.get("lang", "python"), row_code(r))
        if twin:
            dups.add(r["id"])
            continue
        index.add(r["id"], r.get("lang", "python"), row_code(r))
    print("дубликатов по скелету:", len(dups), sorted(dups)[:20])

    bad = set(mismatch) | dups
    keep = [r for r in rows if r["id"] not in bad]
    base_ids = {r["id"] for r in keep if not r.get("persona")}
    orphans = [r["id"] for r in keep if r.get("persona") and r.get("base_id") not in base_ids]
    keep = [r for r in keep if r["id"] not in set(orphans)]
    print("«ворчун»:", sum(1 for r in keep if r.get("persona")), "· без исходного примера (убраны):", len(orphans))
    print("остаётся:", len(keep))
    print("по категориям:", dict(Counter(r["category"] for r in keep)))
    print("по kind:", dict(Counter(r["kind"] for r in keep)))
    print("по языкам:", dict(Counter(r["lang"] for r in keep)))
    wl = sorted(len(r["messages"][-1]["content"].split()) for r in keep)
    print("слов в ответе: медиана", wl[len(wl) // 2], "· 10%", wl[len(wl) // 10], "· 90%", wl[int(len(wl) * .9)])

    random.seed(42)
    random.shuffle(keep)
    with open(ROOT / "explain_ru_full.jsonl", "w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(ROOT / "explain_ru_train.jsonl", "w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps({"messages": r["messages"]}, ensure_ascii=False) + "\n")
    print("записано:", ROOT / "explain_ru_train.jsonl")


if __name__ == "__main__":
    main(rerun="--no-rerun" not in sys.argv)
