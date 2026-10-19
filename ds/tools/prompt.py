"""Готовые промпты из ds/prompts/*.md → в буфер обмена (первый блок ```` … ```` файла).

  ./ds.sh java-prompt          ПРОМПТ из prompts/java_claude.md
  ./ds.sh java-prompt more     ПРОДОЛЖЕНИЕ оттуда же
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gpt  # noqa: E402

FENCE = "`" * 4
BLOCK_RE = re.compile("^" + FENCE + r"\n(.*?)^" + FENCE + "$", re.S | re.M)


def main(argv):
    name = argv[0] if argv else "java_claude"
    which = 1 if argv[1:2] == ["more"] else 0
    path = gpt.ROOT / "prompts" / f"{name}.md"
    blocks = BLOCK_RE.findall(path.read_text(encoding="utf-8"))
    gpt.deliver(blocks[which].rstrip() + "\n", f"{'Продолжение' if which else 'Промпт'} из prompts/{path.name}")
    if not which:
        print("Новый чат Claude → прикрепите файлы практик → Cmd+V. Ответ: Copy → ./ds.sh paste java")


if __name__ == "__main__":
    main(sys.argv[1:])
