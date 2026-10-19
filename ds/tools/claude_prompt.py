"""Промпт «добери датасет одним файлом» для чата Claude — из текущего состояния датасета.

  ./ds.sh claude          60 примеров по 8 самым пустым категориям → в буфер
  ./ds.sh claude 100      другое число примеров

Числа по категориям — пропорционально тому, сколько не хватает до цели (./ds.sh status);
«уже покрыто» — механизмы, которые в датасете уже есть. Каждый новый чат — свежий промпт.
Ответ (файл dataset_batch.py): ./ds.sh add ~/Downloads/dataset_batch.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import coverage  # noqa: E402
import gpt  # noqa: E402

SKIP = {"persona"}          # у «ворчуна» свой процесс: ./ds.sh persona
MAX_CATS = 8


def plan(rows, total: int):
    have = {}
    for r in rows:
        have[r["category"]] = have.get(r["category"], 0) + 1
    need = sorted(((coverage.TARGETS.get(c, 0) - have.get(c, 0), c) for c in gpt.TOPICS
                   if c not in SKIP), reverse=True)
    need = [(k, c) for k, c in need if k > 0][:MAX_CATS]
    if not need:
        raise SystemExit("Все категории добраны до цели — ./ds.sh build и обучение.")
    s = sum(k for k, _ in need)
    out = {c: max(3, round(total * k / s)) for k, c in need}
    return out, have


def main(argv):
    total = int(argv[0]) if argv and argv[0].isdigit() else 60
    rows = coverage.load()
    per, have = plan(rows, total)
    lines_plan = [f"- {c}: {n} примеров (сейчас в датасете {have.get(c, 0)}, цель {coverage.TARGETS.get(c, 0)}; "
                  f"язык кода: {gpt.LANG.get(c, 'python')})" for c, n in per.items()]
    topics = [f"- {c}: {gpt.TOPICS[c]}" for c in per]
    covered = []
    for c in per:
        text = coverage.covered_text(rows, c, limit=15).splitlines()[:20]
        covered.append(f"{c}:\n" + "\n".join("  " + l for l in text))
    tpl = (gpt.ROOT / "prompts" / "claude_full_template.md").read_text(encoding="utf-8")
    text = (tpl.replace("{{TOTAL}}", str(sum(per.values())))
               .replace("{{PLAN}}", "\n".join(lines_plan))
               .replace("{{TOPICS}}", "\n".join(topics))
               .replace("{{COVERED}}", "\n".join(covered))
               .replace("{{FORBIDDEN}}", gpt.FORBIDDEN))
    last = gpt.ROOT / "prompts" / "_last_claude_prompt.md"
    last.write_text(text, encoding="utf-8")
    gpt.deliver(text, f"Промпт для Claude ({sum(per.values())} примеров, {len(per)} категорий)")
    print("Новый чат Claude → Cmd+V. Файл dataset_batch.py скачайте и:\n"
          "  ./ds.sh add ~/Downloads/dataset_batch.py\n"
          "Если Claude прислал блоками в чат: Copy на блоке → ./ds.sh paste\n"
          f"Текст промпта сохранён: ds/prompts/{last.name}")


if __name__ == "__main__":
    main(sys.argv[1:])
