"""Автопроверка ответов на контрольные вопросы: есть ли в ответе ключевые факты.

  python3 tools/score_eval.py ../results/v2/eval_results.json
  python3 tools/score_eval.py a.json b.json        # несколько прогонов рядом

Берёт ответы (ключи вроде base+prompt / tuned / tuned+prompt) и регексы CHECKS из eval_set.py.
✓ — все must нашлись и ни одного must_not; ✗ — иначе (в скобках — что не так). Плюс признаки
зацикливания (повтор одного куска 6+ раз) — типичная поломка после дообучения.
Это грубый фильтр, а не оценка качества: смотрит факты, а не ясность объяснения.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval_set import CHECKS  # noqa: E402

LOOP = re.compile(r"(.{8,60}?)\1{5,}", re.S)


def check(qid: str, text: str) -> tuple[bool, list[str]]:
    rule = CHECKS.get(qid)
    if not rule:
        return True, ["нет правила"]
    why = [f"нет /{r}/" for r in rule.get("must", []) if not re.search(r, text, re.I)]
    why += [f"есть /{r}/" for r in rule.get("must_not", []) if re.search(r, text, re.I)]
    if LOOP.search(text):
        why.append("зацикливание")
    return not why, why


def main(paths):
    for path in paths:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
        variants = [k for k in rows[0] if k not in ("id", "question")]
        totals = {v: 0 for v in variants}
        print(f"\n{path}\n{'id':<5}" + "".join(f"{v:<16}" for v in variants))
        details = []
        for r in rows:
            cells = []
            for v in variants:
                ok, why = check(r["id"], r.get(v, ""))
                totals[v] += ok
                cells.append(f"{'✓' if ok else '✗':<16}")
                if not ok:
                    details.append(f"  {r['id']} {v}: {'; '.join(why)}")
            print(f"{r['id']:<5}" + "".join(cells))
        print("итого" + "".join(f"{f'{totals[v]}/{len(rows)}':<16}" for v in variants))
        print("\n".join(details))


if __name__ == "__main__":
    main(sys.argv[1:] or [str(Path(__file__).resolve().parents[2] / "results" / "v2" / "eval_results.json")])
