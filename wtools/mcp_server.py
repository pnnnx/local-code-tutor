"""MCP-сервер (stdio, JSON-RPC построчно) с инструментами анализа весов — для loca и любого MCP-клиента.

Подключение к loca — `python3 install_loca.py` (добавит сервер в ~/.loca/config.json).
Инструменты возвращают текст с таблицами и всеми числами с графиков + пути к PNG.
"""
from __future__ import annotations

import io
import json
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PATH = {"type": "string", "description": "файл весов (.safetensors/.pt/.bin) или папка адаптера"}
OUT = {"type": "string", "description": "куда сохранить PNG (по умолчанию ./weights_report)"}
TOOLS = [
    {"name": "weights_inspect",
     "description": "Что внутри модели: тензоры, формы, dtype, число параметров, память fp32/fp16/int8/int4, "
                    "крупнейшие блоки. + PNG: доля параметров по блокам.",
     "inputSchema": {"type": "object", "properties": {"path": PATH, "out": OUT}, "required": ["path"]}},
    {"name": "weights_stats",
     "description": "Статистика весов по слоям: mean/std/RMS/|max|, выбросы >6σ, нулевые строки, разреженность. "
                    "+ PNG: RMS по глубине и гистограмма (tensor — какого тензора).",
     "inputSchema": {"type": "object", "properties": {"path": PATH, "out": OUT,
                                                      "tensor": {"type": "string"}}, "required": ["path"]}},
    {"name": "weights_diff",
     "description": "Сравнение двух чекпоинтов (до/после дообучения): ‖ΔW‖, ‖ΔW‖/‖W‖, косинус по слоям, "
                    "топ изменившихся, по типам модулей. + PNG.",
     "inputSchema": {"type": "object", "properties": {"before": PATH, "after": PATH, "out": OUT},
                     "required": ["before", "after"]}},
    {"name": "weights_lora",
     "description": "LoRA-адаптер (PEFT): ΔW = B·A·alpha/r по модулям, норма, эффективный ранг, спектр, "
                    "какие модули меняются сильнее. + PNG.",
     "inputSchema": {"type": "object", "properties": {"path": PATH, "out": OUT}, "required": ["path"]}},
    {"name": "weights_quant",
     "description": "Ошибка квантования int8/int4 по слоям: масштаб на тензор / на строку / блоками по 32 "
                    "(как GGUF). + PNG.",
     "inputSchema": {"type": "object", "properties": {"path": PATH, "out": OUT,
                                                      "bits": {"type": "integer", "enum": [8, 4]}},
                     "required": ["path"]}},
]


def call(name: str, args: dict) -> str:
    import weights as w
    out = args.get("out") or "weights_report"
    if name == "weights_inspect":
        text, pngs = w.inspect(args["path"], out=out)
    elif name == "weights_stats":
        text, pngs = w.stats(args["path"], out=out, tensor=args.get("tensor"))
    elif name == "weights_diff":
        text, pngs = w.diff(args["before"], args["after"], out=out)
    elif name == "weights_lora":
        text, pngs = w.lora(args["path"], out=out)
    elif name == "weights_quant":
        text, pngs = w.quant(args["path"], out=out, bits=int(args.get("bits") or 4))
    else:
        raise ValueError(f"нет инструмента {name}")
    return text + ("\n\nГрафики (PNG):\n" + "\n".join(f"- {p}" for p in pngs) if pngs else "")


def reply(msg_id, result=None, error=None) -> None:
    msg = {"jsonrpc": "2.0", "id": msg_id}
    msg["error" if error else "result"] = error or result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:
            continue                                   # уведомления
        if method == "initialize":
            reply(mid, {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "weights", "version": "0.1"}})
        elif method == "tools/list":
            reply(mid, {"tools": TOOLS})
        elif method == "tools/call":
            p = msg.get("params", {})
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):             # stdout занят протоколом
                    text = call(p.get("name"), p.get("arguments") or {})
                reply(mid, {"content": [{"type": "text", "text": text}]})
            except SystemExit as e:
                reply(mid, {"content": [{"type": "text", "text": str(e)}], "isError": True})
            except Exception as e:  # noqa: BLE001
                reply(mid, {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}\n"
                                         + traceback.format_exc(limit=3)}], "isError": True})
        elif method == "ping":
            reply(mid, {})
        else:
            reply(mid, error={"code": -32601, "message": f"нет метода {method}"})


if __name__ == "__main__":
    main()
