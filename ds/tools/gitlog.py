"""Автокоммит принятых примеров: каждая порция датасета — markdown-коммит с причинами отказов.

Коммитятся только переданные файлы (ds/parts/..., ds/batches/...), чужие правки не захватываются.
Отключить: DS_NO_GIT=1 ./ds.sh ...
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

TRAILER = ("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01WkKKkgX3tYidcpeWqdA7MQ")


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def commit(paths, title: str, what: str, how: str, why: str, check: str) -> bool:
    if os.environ.get("DS_NO_GIT"):
        return False
    paths = [Path(p) for p in paths if p and Path(p).exists()]
    if not paths:
        return False
    cwd = paths[0].parent
    top = _git(["rev-parse", "--show-toplevel"], cwd)
    if top.returncode != 0:
        return False
    root = Path(top.stdout.strip())
    rel = [str(p.resolve().relative_to(root.resolve())) for p in paths]
    msg = (f"{title}\n\n## Что\n{what}\n\n## Как\n{how}\n\n## Зачем\n{why}\n\n"
           f"## Проверка\n{check}\n\n{TRAILER}\n")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(msg)
    try:
        _git(["add", "--", *rel], root)
        r = _git(["commit", "-q", "-F", f.name, "--", *rel], root)
    finally:
        os.unlink(f.name)
    if r.returncode == 0:
        print(f"   git: {title}")
        return True
    print("   git: не закоммитилось — " + (r.stdout + r.stderr).strip().splitlines()[-1][:200])
    return False
