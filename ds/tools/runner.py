"""Запуск фрагмента кода и получение «наблюдаемого вывода».

Вывод = stdout; если процесс упал — плюс ПОСЛЕДНЯЯ строка stderr (тип и текст исключения/ошибки),
чтобы пути к временным файлам в traceback не мешали сравнению.

lang: python | javascript | c | cpp | java | sql | none
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 15
# Тот же интерпретатор, что запустил проверку, и БЕЗ -I: флаг -I отключает пакеты,
# поставленные через `pip install --user` (pandas, torch…), и код падал с ModuleNotFoundError.
PYTHON = sys.executable or "python3"


def _env():
    env = {k: v for k, v in os.environ.items() if k != "JAVA_TOOL_OPTIONS"}
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MPLBACKEND"] = "Agg"
    return env


def _run(cmd, cwd, stdin_text=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, input=stdin_text, capture_output=True, text=True,
                           timeout=TIMEOUT, env=_env(), errors="replace")
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT"
    return p.returncode, p.stdout, p.stderr


def _combine(code, out, err):
    out = out.rstrip()
    if code != 0:
        lines = [l for l in err.strip().splitlines() if l.strip() and not l.startswith("Picked up JAVA_TOOL_OPTIONS")]
        last = lines[-1].strip() if lines else f"exit code {code}"
        out = (out + "\n" if out else "") + "[stderr] " + last
    return out


def run_sql(code: str) -> str:
    """SQL-скрипт в sqlite в памяти. Печатает результат каждого запроса, возвращающего строки."""
    con = sqlite3.connect(":memory:")
    outs = []
    # делим по ';' в конце строки (без хитрого парсинга — в примерах не используйте ';' внутри строк)
    stmts = [s.strip() for s in re.split(r";\s*(?:\n|$)", code) if s.strip()]
    for s in stmts:
        try:
            cur = con.execute(s)
        except Exception as e:  # noqa: BLE001
            outs.append(f"[error] {type(e).__name__}: {e}")
            break
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            outs.append(" | ".join(cols))
            for r in rows:
                outs.append(" | ".join("NULL" if v is None else str(v) for v in r))
            outs.append(f"({len(rows)} rows)")
    return "\n".join(outs)


def missing_modules(mods) -> list[str]:
    """Каких модулей нет у того же интерпретатора, которым запускаются примеры."""
    miss = []
    for m in sorted(set(mods)):
        if m in sys.builtin_module_names:
            continue
        code, _out, _err = _run([PYTHON, "-c", f"import {m}"], tempfile.gettempdir())
        if code != 0:
            miss.append(m)
    return miss


def run_code(lang: str, code: str, stdin_text: str | None = None) -> str | None:
    lang = (lang or "none").lower()
    if lang in ("none", "", "text"):
        return None
    if lang == "sql":
        return run_sql(code)
    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        if lang == "python":
            f = dp / "main.py"; f.write_text(code)
            return _combine(*_run([PYTHON, str(f)], d, stdin_text))
        if lang in ("javascript", "js"):
            f = dp / "main.js"; f.write_text(code)
            return _combine(*_run(["node", str(f)], d, stdin_text))
        if lang == "c":
            f = dp / "main.c"; f.write_text(code)
            c, o, e = _run(["gcc", "-O0", "-w", "-std=c11", str(f), "-o", str(dp / "a.out"), "-lm"], d)
            if c != 0:
                return "[compile error] " + (e.strip().splitlines() or ["?"])[0]
            return _combine(*_run([str(dp / "a.out")], d, stdin_text))
        if lang == "cpp":
            f = dp / "main.cpp"; f.write_text(code)
            c, o, e = _run(["g++", "-O0", "-w", "-std=c++17", str(f), "-o", str(dp / "a.out")], d)
            if c != 0:
                return "[compile error] " + (e.strip().splitlines() or ["?"])[0]
            return _combine(*_run([str(dp / "a.out")], d, stdin_text))
        if lang == "java":
            m = re.search(r"public\s+class\s+(\w+)", code)
            name = m.group(1) if m else "Main"
            f = dp / f"{name}.java"; f.write_text(code)
            c, o, e = _run(["javac", "-nowarn", str(f)], d)
            if c != 0:
                lines = [l for l in e.strip().splitlines() if not l.startswith("Picked up")]
                return "[compile error] " + (lines[0] if lines else "?")
            return _combine(*_run(["java", "-cp", d, name], d, stdin_text))
    raise ValueError(f"unknown lang {lang}")


if __name__ == "__main__":
    import sys
    print(run_code(sys.argv[1], Path(sys.argv[2]).read_text()))
