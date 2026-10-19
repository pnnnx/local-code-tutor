"""Поиск дубликатов: не только копий, но и «тот же пример с другими именами».

ChatGPT (и любая модель) охотно повторяет классику: один и тот же трюк с переименованными
переменными в соседних ответах и в разных чатах. Поэтому код сравнивается по «скелету»:
имена → ID, строки → S, числа → N, пробелы схлопнуты. Два примера с одинаковым скелетом
(похожесть ≥ порога) — дубликат, даже если в одном `users`, а в другом `orders`.
"""
from __future__ import annotations

import difflib
import io
import json
import keyword
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_RE = re.compile(r"```(\w*)\n(.*?)```", re.S)
THRESHOLD = 0.88

_PY_KEEP = set(keyword.kwlist) | {
    "print", "len", "range", "list", "dict", "set", "tuple", "str", "int", "float", "bool",
    "sum", "min", "max", "sorted", "enumerate", "zip", "map", "filter", "open", "isinstance",
    "super", "self", "cls", "None", "True", "False", "lambda", "yield", "async", "await"}
_GENERIC_KEEP = {
    # js / java / c / sql — ключевые слова, от которых зависит механизм
    "var", "let", "const", "function", "this", "new", "return", "class", "extends", "async",
    "await", "if", "else", "for", "while", "switch", "case", "break", "null", "undefined",
    "true", "false", "typeof", "public", "static", "void", "int", "long", "char", "double",
    "String", "Integer", "equals", "struct", "unsigned", "sizeof", "printf", "malloc", "free",
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "INNER", "GROUP", "BY", "HAVING", "ORDER",
    "NULL", "NOT", "IN", "EXISTS", "COUNT", "SUM", "AVG", "OVER", "PARTITION", "WITH", "AS",
    "CASE", "WHEN", "THEN", "END", "UNION", "ALL", "DISTINCT", "INSERT", "INTO", "VALUES",
    "CREATE", "TABLE", "UPDATE", "DELETE", "SET", "ON", "AND", "OR", "IS", "LIKE", "LIMIT"}


def skeleton(code: str, lang: str = "python") -> str:
    code = code or ""
    if lang == "python":
        try:
            out = []
            for tok in tokenize.generate_tokens(io.StringIO(code).readline):
                if tok.type == tokenize.NAME:
                    out.append(tok.string if tok.string in _PY_KEEP else "ID")
                elif tok.type == tokenize.STRING:
                    out.append("S")
                elif tok.type == tokenize.NUMBER:
                    out.append("N")
                elif tok.type == tokenize.OP:
                    out.append(tok.string)
                elif tok.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                    out.append({tokenize.NEWLINE: ";", tokenize.INDENT: "{", tokenize.DEDENT: "}"}[tok.type])
            return " ".join(out)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass
    if lang == "sql":
        # таблицы и данные — шаблон, суть примера в запросах: сравниваем только их
        stmts = [st for st in re.split(r";\s*", code)
                 if st.strip() and not re.match(r"\s*(CREATE|INSERT)\b", st, re.I)]
        code = ";\n".join(stmts)
    text = re.sub(r"(\"[^\"\n]*\"|'[^'\n]*')", "S", code)
    text = re.sub(r"\b\d+(\.\d+)?\b", "N", text)
    keep = _GENERIC_KEEP | {k.lower() for k in _GENERIC_KEEP}
    text = re.sub(r"\b[A-Za-z_]\w*\b", lambda m: m.group(0) if m.group(0) in keep else "ID", text)
    return re.sub(r"\s+", " ", text).strip()


def similar(a: str, b: str, threshold: float = THRESHOLD) -> bool:
    if not a or not b:
        return False
    la, lb = len(a), len(b)
    if 2 * min(la, lb) / (la + lb) < threshold:      # по длине уже не дотянуть до порога
        return False
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sm.real_quick_ratio() >= threshold and sm.quick_ratio() >= threshold and sm.ratio() >= threshold


def row_code(row: dict) -> str:
    if row.get("code"):
        return row["code"]
    m = CODE_RE.search(row["messages"][0]["content"])
    return m.group(2) if m else row["messages"][0]["content"]


class Index:
    """Скелеты всех уже принятых примеров — чтобы отсекать повторы ещё на build."""

    def __init__(self, rows: list[dict] | None = None):
        self.items: list[tuple[str, str, str]] = []      # (id, lang, skeleton)
        for r in rows or []:
            self.add(r["id"], r.get("lang", "python"), row_code(r))

    @classmethod
    def from_parts(cls, parts_dir: Path | None = None, exclude_file: Path | None = None) -> "Index":
        rows = []
        for p in sorted((parts_dir or ROOT / "parts").glob("*.jsonl")):
            if exclude_file and p.resolve() == exclude_file.resolve():
                pass       # свой файл тоже учитываем — повтор внутри части тоже дубль
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    if not row.get("persona"):     # «ворчун» — тот же код, что у исходного примера
                        rows.append(row)
        return cls(rows)

    def add(self, item_id: str, lang: str, code: str) -> None:
        self.items.append((item_id, lang, skeleton(code, lang)))

    def find(self, lang: str, code: str, threshold: float = THRESHOLD) -> str | None:
        sk = skeleton(code, lang)
        for item_id, item_lang, other in self.items:
            if item_lang == lang and similar(sk, other, threshold):
                return item_id
        return None
