"""Подключить инструменты весов к loca: добавляет MCP-сервер "weights" в ~/.loca/config.json.

  python3 install_loca.py          # один раз; потом в loca: /mcp — сервер weights и 5 инструментов
Нужны torch, safetensors, matplotlib (в coder/ds: ./ds.sh setup).
"""
import json
import os
import sys
from pathlib import Path

home = Path(os.environ.get("LOCA_HOME", Path.home() / ".loca"))
cfg_path = home / "config.json"
cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
server = Path(__file__).resolve().parent / "mcp_server.py"
cfg.setdefault("mcp_servers", {})["weights"] = {"command": sys.executable, "args": [str(server)]}
home.mkdir(parents=True, exist_ok=True)
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Готово: {cfg_path} → mcp_servers.weights = {sys.executable} {server}")
missing = [m for m in ("torch", "safetensors", "matplotlib") if __import__("importlib").util.find_spec(m) is None]
if missing:
    print(f"⚠ Для этого python не установлено: {', '.join(missing)} → {sys.executable} -m pip install --user {' '.join(missing)}")
