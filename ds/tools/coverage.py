"""Что уже есть в датасете и сколько не хватает — и список для вставки в ChatGPT.

  python3 tools/coverage.py              # таблица: категория · есть · цель · не хватает · kind
  python3 tools/coverage.py py_scope     # для чата: какие механизмы уже покрыты (не повторять)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Цель ≈ 2000 примеров. Больше всего не хватает аналитики, разбора программ, Java.
TARGETS = {
    "py_scope": 90, "py_mutability": 90, "py_eval": 90, "py_iter": 90,
    "py_oop": 100, "py_functions": 100, "py_data": 100, "py_errors_io": 90,
    "py_algorithms": 120, "py_systems": 150, "py_bugs": 120, "py_async_types": 60,
    "py_pandas": 200, "py_dashboards": 150, "sql": 90, "sql_analytics": 150,
    "js": 100, "c_cpp": 80, "java": 70,
    "ml_weights": 150, "ml_pytorch": 80, "ml_classic": 60,
    "persona": 300,      # режим «ворчун» (./ds.sh persona): реакции поверх готовых примеров
}
MECH_RE = re.compile(r"\*\*Механизм\s*[—–-]\s*([^*\n]{3,90}?)[.:]?\*\*", re.I)


def load():
    rows = []
    for p in sorted((ROOT / "parts").glob("*.jsonl")):
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


def table(rows):
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    total_have = total_target = 0
    print(f"{'категория':<16}{'есть':>6}{'цель':>6}{'нужно':>7}   kind")
    for cat in sorted(set(TARGETS) | set(by_cat), key=lambda c: -(TARGETS.get(c, 0) - len(by_cat[c]))):
        have, target = len(by_cat[cat]), TARGETS.get(cat, 0)
        kinds = Counter(r["kind"] for r in by_cat[cat])
        print(f"{cat:<16}{have:>6}{target:>6}{max(0, target - have):>7}   "
              + " ".join(f"{k}:{v}" for k, v in kinds.most_common()))
        total_have += have
        total_target += target
    print(f"{'ИТОГО':<16}{total_have:>6}{total_target:>6}{max(0, total_target - total_have):>7}")


def next_gpt_number(rows, cat):
    nums = [int(m.group(1)) for r in rows if r["category"] == cat
            for m in [re.search(r"-g(\d+)$", r["id"])] if m]
    return (max(nums) if nums else 0) + 1


def covered_text(rows, cat, limit: int = 60) -> str:
    """Список «уже покрыто» для промпта: механизмы из заголовков **Механизм — …**."""
    mechs, firsts = Counter(), []
    for r in rows:
        if r["category"] != cat:
            continue
        m = MECH_RE.search(r["messages"][1]["content"])
        if m:
            mechs[m.group(1).strip().lower()] += 1
        else:       # механизм не подписан — берём суть вопроса
            firsts.append(re.sub(r"\s+", " ", r["messages"][0]["content"].split("```", 1)[0])[:110].strip())
    lines = [f"- {mech}" + (f" (×{n})" if n > 1 else "") for mech, n in mechs.most_common(limit)]
    lines += [f"- {f}" for f in firsts[:25]]
    return "\n".join(lines) or "- (пока ничего)"


def for_gpt(rows, cat):
    rs = [r for r in rows if r["category"] == cat]
    mechs = Counter()
    firsts = []
    for r in rs:
        m = MECH_RE.search(r["messages"][1]["content"])
        if m:
            mechs[m.group(1).strip().lower()] += 1
        else:
            first = r["messages"][1]["content"].split("\n", 1)[0]
            firsts.append(re.sub(r"\s+", " ", first)[:90])
    kinds = Counter(r["kind"] for r in rs)
    target = TARGETS.get(cat, 0)
    print(f"Категория {cat}: уже {len(rs)} примеров (цель {target}), kind: "
          + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
    gpt_ids = [int(m.group(1)) for r in rs for m in [re.search(r"-g(\d+)$", r["id"])] if m]
    print(f"Следующий id: {cat}-g{(max(gpt_ids) if gpt_ids else 0) + 1:03d}")
    print("\nУЖЕ ПОКРЫТО — не повторяй эти механизмы в той же форме, ищи новые ситуации и ракурсы:")
    for mech, n in mechs.most_common(60):
        print(f"- {mech}" + (f" (×{n})" if n > 1 else ""))
    for f in firsts[:25]:
        print(f"- {f}")


if __name__ == "__main__":
    rows = load()
    if len(sys.argv) > 1:
        for_gpt(rows, sys.argv[1])
    else:
        table(rows)
