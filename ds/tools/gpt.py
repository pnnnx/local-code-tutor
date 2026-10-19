"""Сбор датасета через ChatGPT в три команды (см. README.md).

  ./ds.sh                      ПРОЩЕ ВСЕГО: выбрать тему и идти по шагам (Enter после каждого Copy)
  ./ds.sh go py_pandas         то же для конкретной темы
  ./ds.sh new py_pandas        промпт для НОВОГО чата → в буфер обмена
  ./ds.sh more py_pandas       «ещё N примеров» для того же чата → в буфер
  ./ds.sh paste py_pandas      ответ ChatGPT из буфера → проверка → в датасет
  ./ds.sh add batches/x.py     то же для сохранённого файла

Ответ ChatGPT проверяется build.py (код реально запускается, дубликаты отсекаются).
Годные примеры записываются сразу, а для плохих готовится сообщение «исправь» — тоже в буфер.
id ChatGPT не важны: при записи примеры перенумеровываются в <категория>-gNNN.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from runner import missing_modules  # noqa: E402
import coverage  # noqa: E402
import gitlog  # noqa: E402

# Тексты (темы, промпты) лежат в gpt_data.json: очень длинные строки с кириллицей
# системный Python 3.9 на macOS читает из .py с ошибкой «Non-UTF-8 code».
DATA = json.loads((HERE / "gpt_data.json").read_text(encoding="utf-8"))
TOPICS = DATA["topics"]
SIZE = DATA["size"]
LANG = DATA["lang"]
FORBIDDEN = DATA["forbidden"]
NEW_TEMPLATE = DATA["templates"]["new"]
MORE_TEMPLATE = DATA["templates"]["more"]
FIX_TEMPLATE = DATA["templates"]["fix"]


# ---------------------------------------------------------------- буфер обмена
def to_clipboard(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text.encode("utf-8"), check=False)
            return True
    return False


def from_clipboard() -> str:
    for cmd in (["pbpaste"], ["wl-paste"], ["xclip", "-selection", "clipboard", "-o"]):
        if shutil.which(cmd[0]):
            return subprocess.run(cmd, capture_output=True, check=False).stdout.decode("utf-8", "replace")
    raise SystemExit("Нет доступа к буферу обмена: сохраните ответ в файл и запустите ./ds.sh add файл")


def deliver(text: str, what: str) -> None:
    if to_clipboard(text):
        print(f"📋 {what} — в буфере обмена. Вставьте в ChatGPT (Cmd+V).")
    else:
        print(text)


# ---------------------------------------------------------------- команды
def cmd_new(cat: str, n: int | None = None) -> None:
    if cat not in TOPICS:
        raise SystemExit(f"Неизвестная категория {cat}. Есть: {', '.join(TOPICS)}")
    rows = coverage.load()
    text = NEW_TEMPLATE.format(n=n or SIZE.get(cat, 8), cat=cat, lang=LANG.get(cat, "python"),
                               topics=TOPICS[cat], covered=coverage.covered_text(rows, cat),
                               forbidden=FORBIDDEN)
    deliver(text, f"Промпт для нового чата ({cat})")


def cmd_more(cat: str, n: int | None = None) -> None:
    deliver(MORE_TEMPLATE.format(n=n or SIZE.get(cat, 8), cat=cat), "Продолжение")


def load_examples(path: Path):
    spec = importlib.util.spec_from_file_location("gpt_batch", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SyntaxError as e:
        raise SystemExit(f"Файл не разбирается как Python ({e}). Скопируйте ответ ChatGPT целиком, "
                         "это должен быть один блок «EXAMPLES = [...]».")
    exs = getattr(mod, "EXAMPLES", None)
    if not isinstance(exs, list) or not exs:
        raise SystemExit("В файле нет списка EXAMPLES.")
    return exs


MISSING_RE = re.compile(r"No module named '([\w.]+)'")
PIP_NAMES = {"sklearn": "scikit-learn", "cv2": "opencv-python", "PIL": "pillow", "yaml": "pyyaml"}


def insert_code(ex: dict) -> None:
    """write-пример, где ChatGPT показал только вывод, а код решения в ответ не вставил:
    вставляем код сами после первого абзаца — проверять его всё равно будем запуском."""
    if ex.get("kind") != "write" or not ex.get("code") or build.norm(ex["code"]) in build.norm(ex.get("answer", "")):
        return
    fence = {"javascript": "javascript", "sql": "sql", "java": "java", "c": "c", "cpp": "cpp"}.get(ex.get("lang"), "python")
    head, sep, rest = ex["answer"].partition("\n\n")
    block = f"```{fence}\n{ex['code'].rstrip()}\n```"
    ex["answer"] = f"{head}\n\n{block}\n\n{rest}" if sep else f"{head}\n\n{block}"


def into_batches(path: Path) -> Path:
    """Файл не из batches/ (например, ~/Downloads от Claude) — копия в batches/: она и коммитится."""
    path = Path(path).expanduser().resolve()
    batches = (ROOT / "batches").resolve()
    if path.parent == batches:
        return path
    batches.mkdir(exist_ok=True)
    n = 1
    while (batches / f"{path.stem}_{n:02d}.py").exists():
        n += 1
    dst = batches / f"{path.stem}_{n:02d}.py"
    dst.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Копия: batches/{dst.name}")
    return dst


def cmd_add(path: Path, cat: str | None = None):
    """Проверка и запись пачки. Без cat пачка может быть смешанной: каждая категория — отдельно."""
    path = into_batches(path)
    exs = [dict(e) for e in load_examples(path)]
    for e in exs:
        insert_code(e)
    if cat:
        groups = {cat: exs}
    else:
        groups = {}
        for e in exs:
            groups.setdefault(str(e.get("category") or "").strip(), []).append(e)
        unknown = [c for c in groups if c not in TOPICS]
        if unknown:
            raise SystemExit(f"Неизвестные категории: {', '.join(repr(c) for c in unknown)}. "
                             f"Есть: {', '.join(TOPICS)}. Или укажите: ./ds.sh add файл категория")
    # сначала — не хватает ли библиотек: это проблема компьютера, а не примеров
    imports = set()
    for e in exs:
        if e.get("run") is False or e.get("lang", "python") != "python":
            continue
        imports |= set(re.findall(r"^\s*(?:import|from)\s+(\w+)", e.get("code", ""), re.M))
    missing = set(missing_modules(imports))
    if missing:
        names = " ".join(sorted(PIP_NAMES.get(m, m) for m in missing))
        print(f"⚠ На этом компьютере не установлено: {', '.join(sorted(missing))}. Примеры ещё не проверялись.\n"
              f"  Установите:  python3 -m pip install --user {names}\n"
              "  (или сразу всё нужное: ./ds.sh setup)")
        return "env"
    all_bad, written_total = [], 0
    for c, group in groups.items():
        written, bad = _add_group(path, c, group)
        written_total += written
        all_bad += bad
    if len(groups) > 1:
        print(f"\nВсего принято {written_total} из {len(exs)}.")
    if not all_bad:
        return 0
    problems = "\n".join(f"- {e.get('gpt_id')}: " + "; ".join(errs)
                         + (f" | реальный вывод: {obs!r}" if obs else "") for e, errs, obs in all_bad)
    deliver(FIX_TEMPLATE.format(problems=problems), f"Сообщение «исправь {len(all_bad)} примеров»")
    print("Исправленный ответ — снова: ./ds.sh paste " + (cat or "<категория>") if cat
          else "Исправленный ответ сохраните в файл и: ./ds.sh add файл")
    return len(all_bad)


def _add_group(path: Path, cat: str, exs: list[dict]):
    rows = coverage.load()
    num = coverage.next_gpt_number(rows, cat)
    for e in exs:                       # модели путают id — нумеруем сами
        e["gpt_id"] = e.get("id", "?")
        e["id"] = f"{cat}-g{num:03d}"
        e["category"] = cat
        num += 1
    out = ROOT / "parts" / f"gpt_{cat}.jsonl"
    print(f"\n— {cat}: {len(exs)} примеров")
    written, bad = build.process(exs, out, partial=True,
                                 label=lambda e: f"{e['id']} (в ответе: {e.get('gpt_id')})")
    print(f"Принято {written} из {len(exs)}.")
    if written:
        total = sum(1 for l in out.read_text(encoding="utf-8").splitlines() if l.strip())
        target = coverage.TARGETS.get(cat, 0)
        rej = "\n".join(f"- {e.get('gpt_id')}: " + "; ".join(errs) for e, errs, _ in bad) or "- нет"
        gitlog.commit(
            [out, path], f"ds: +{written} {cat} (всего {total})",
            f"Принято {written} из {len(exs)} примеров в `{cat}`; "
            f"`ds/parts/{out.name}`: {total}. Сырой ответ — `ds/batches/{path.name}`.",
            "`./ds.sh` → ChatGPT/Claude → запуск кода и проверки `build.py` → годные в `ds/parts/`.",
            f"Датасет v3 (этап 2 `PLAN.md`): `{cat}` — {total} из цели {target} (в этом файле).",
            "Отклонено:\n" + rej)
    return written, bad


def extract_examples(text: str) -> str | None:
    """Код с EXAMPLES из ответа ChatGPT. Внутри ответов тоже есть блоки ```, поэтому
    режем не по первому ```, а от «EXAMPLES» до конца (снимая закрывающий ``` всего ответа)."""
    i = text.find("EXAMPLES")
    if i < 0:
        return None
    body = text[i:].rstrip()
    body = re.sub(r"\n?[`~]{3,}\s*$", "", body).rstrip()    # закрывающий ``` или ```` всего ответа
    return body + "\n"


def complete(text: str) -> bool:
    """Ответ скопирован целиком — это корректный Python."""
    try:
        compile(text, "<chatgpt>", "exec")
        return True
    except SyntaxError:
        return False


def save_batch(text: str, cat: str) -> Path:
    batches = ROOT / "batches"
    batches.mkdir(exist_ok=True)
    n = 1
    while (batches / f"gpt_{cat}_{n:02d}.py").exists():
        n += 1
    path = batches / f"gpt_{cat}_{n:02d}.py"
    path.write_text(text, encoding="utf-8")
    print(f"Сохранено: batches/{path.name}")
    return path


def cmd_paste(cat: str) -> None:
    text = extract_examples(from_clipboard())
    if text is None:
        raise SystemExit("В буфере нет «EXAMPLES = [...]». Скопируйте блок кода из ответа ChatGPT (кнопка Copy).")
    if not complete(text):
        raise SystemExit("Скопирован не весь ответ (обрывается). Нажмите Copy у большого блока «EXAMPLES = [...]» в конце ответа ChatGPT.")
    cmd_add(save_batch(text, cat), cat)


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"


def cmd_go(cat: str, n: int | None = None, rounds_per_chat: int = 6) -> None:
    """Пошаговый режим: сам кладёт в буфер нужный промпт и сам забирает ответ ChatGPT."""
    if cat not in TOPICS:
        raise SystemExit(f"Неизвестная категория {cat}. Есть: {', '.join(TOPICS)}")
    cmd_new(cat, n)
    print("\n① Откройте НОВЫЙ чат ChatGPT → Cmd+V → отправьте.")
    last = from_clipboard()
    rounds = 0
    while True:
        print("② Когда ChatGPT ответит — нажмите кнопку Copy на блоке кода и вернитесь сюда.")
        if ask("   Enter — проверить ответ · q — выход › ") in ("q", "й", "exit", "выход"):
            print("Готово. Итоговый файл для обучения: ./ds.sh build")
            return
        raw = from_clipboard()
        if raw == last:
            print("   ⚠ Буфер не изменился — нажмите Copy именно на ответе ChatGPT.\n")
            continue
        text = extract_examples(raw)
        if text is None:
            print("   ⚠ В буфере не ответ ChatGPT (нет «EXAMPLES = [...]»). Нажмите Copy на блоке кода.\n")
            last = raw
            continue
        if not complete(text):
            print("   ⚠ Скопирован не весь ответ: похоже, нажали Copy на маленьком блоке ВНУТРИ ответа.\n"
                  "     Прокрутите ответ ChatGPT до самого конца и нажмите Copy у большого блока «EXAMPLES = [...]».\n")
            last = raw
            continue
        path = save_batch(text, cat)
        bad = cmd_add(path, cat)
        while bad == "env":
            if ask("   Установите и нажмите Enter — проверю этот же ответ ещё раз · q — выход › ") in ("q", "й"):
                return
            bad = cmd_add(path, cat)
        rounds += 1
        if bad:
            print(f"③ В буфере — просьба исправить {bad} примеров. Вставьте в ТОТ ЖЕ чат (Cmd+V).\n")
        elif rounds >= rounds_per_chat:
            rounds = 0
            cmd_new(cat, n)
            print("③ Чат стал длинным — дальше будут повторы. Откройте НОВЫЙ чат → Cmd+V.\n")
        else:
            cmd_more(cat, n)
            print("③ В буфере — «ещё порция». Вставьте в ТОТ ЖЕ чат (Cmd+V).\n")
        last = from_clipboard()


def menu() -> None:
    rows = coverage.load()
    have = {}
    for r in rows:
        have[r["category"]] = have.get(r["category"], 0) + 1
    need = sorted(((coverage.TARGETS.get(c, 0) - have.get(c, 0), c) for c in TOPICS), reverse=True)
    need = [(k, c) for k, c in need if k > 0]
    print("Сколько не хватает (собирайте сверху вниз):")
    for i, (k, c) in enumerate(need[:12], 1):
        print(f"  {i:>2}. {c:<15} ещё {k}")
    print("   p. режим «ворчун» — реакции с матом поверх готовых примеров")
    choice = ask("Номер или название категории (Enter — первая) › ")
    if choice in ("q", "й"):
        return
    if choice in ("p", "з", "persona"):
        import persona
        persona.go()
        return
    if not choice:
        cat = need[0][1]
    elif choice.isdigit() and 1 <= int(choice) <= len(need):
        cat = need[int(choice) - 1][1]
    else:
        cat = choice
    cmd_go(cat)


def main(argv):
    if not argv or argv[0] == "menu":
        menu()
        return
    if argv[:1] == ["paste"] and len(argv) == 1:     # смешанная пачка (Claude): категории — из примеров
        text = extract_examples(from_clipboard())
        if text is None or not complete(text):
            raise SystemExit("В буфере нет целого блока «EXAMPLES = [...]». Copy на блоке ответа.")
        cmd_add(save_batch(text, "mixed"), None)
        return
    if len(argv) < 2 or argv[0] not in ("new", "more", "paste", "add", "go"):
        print(__doc__)
        return
    cmd, arg = argv[0], argv[1]
    n = int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else None
    if cmd == "go":
        cmd_go(arg, n)
    elif cmd == "new":
        cmd_new(arg, n)
    elif cmd == "more":
        cmd_more(arg, n)
    elif cmd == "paste":
        cmd_paste(arg)
    else:
        cmd_add(Path(arg), argv[2] if len(argv) > 2 else None)


if __name__ == "__main__":
    main(sys.argv[1:])
