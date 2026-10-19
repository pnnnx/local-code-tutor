"""Тесты инструментов анализа весов на крошечной «модели» с именами как у Qwen/LLaMA.

  python3 -m pytest -q wtools/test_weights.py
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import weights as w  # noqa: E402

HERE = Path(__file__).resolve().parent


def tiny_state(seed=0):
    g = torch.Generator().manual_seed(seed)
    s = {"model.embed_tokens.weight": torch.randn(50, 16, generator=g) * 0.02}
    for i in range(3):
        p = f"model.layers.{i}."
        for m in ("q_proj", "k_proj", "v_proj", "o_proj"):
            s[p + f"self_attn.{m}.weight"] = torch.randn(16, 16, generator=g) * 0.05
        s[p + "mlp.up_proj.weight"] = torch.randn(32, 16, generator=g) * 0.05
        s[p + "mlp.down_proj.weight"] = torch.randn(16, 32, generator=g) * 0.05
        s[p + "input_layernorm.weight"] = torch.ones(16)
    s["lm_head.weight"] = torch.randn(50, 16, generator=g) * 0.02
    return s


@pytest.fixture()
def files(tmp_path):
    from safetensors.torch import save_file
    before = tiny_state()
    after = {k: v.clone() for k, v in before.items()}
    after["model.layers.2.mlp.up_proj.weight"] += 0.05            # сильно изменённый слой
    after["model.layers.0.self_attn.q_proj.weight"][0, 0] = 3.0   # выброс
    after["model.layers.1.mlp.down_proj.weight"][3] = 0.0         # мёртвая строка
    save_file(before, str(tmp_path / "before.safetensors"))
    torch.save({"state_dict": after}, tmp_path / "after.pt")
    ad = tmp_path / "adapter"
    ad.mkdir()
    g = torch.Generator().manual_seed(1)
    lora = {}
    for i in range(3):
        for m, (o, n) in {"q_proj": (16, 16), "v_proj": (16, 16), "up_proj": (32, 16)}.items():
            base = f"base_model.model.model.layers.{i}.{'mlp' if m == 'up_proj' else 'self_attn'}.{m}"
            lora[base + ".lora_A.weight"] = torch.randn(4, n, generator=g)
            lora[base + ".lora_B.weight"] = torch.randn(o, 4, generator=g) * (0.1 if m != "up_proj" else 0.5)
    save_file(lora, str(ad / "adapter_model.safetensors"))
    (ad / "adapter_config.json").write_text(json.dumps({"r": 4, "lora_alpha": 8}))
    return tmp_path


def test_inspect(files):
    text, pngs = w.inspect(files / "before.safetensors", out=files / "rep")
    total = sum(t.numel() for t in tiny_state().values())
    assert f"параметров: {total:,}".replace(",", " ") in text
    assert "model.layers.0" in text and Path(pngs[0]).stat().st_size > 1000


def test_stats_flags_outlier_and_dead_row(files):
    text, pngs = w.stats(files / "after.pt", out=files / "rep")
    assert "model.layers.0.self_attn.q_proj.weight: 1 выбросов" in text
    assert "model.layers.1.mlp.down_proj.weight: 1 нулевых строк" in text
    assert "гистограмма model.layers.0.self_attn.q_proj.weight" in text   # самый «хвостатый» тензор
    assert len(pngs) == 2 and all(Path(p).exists() for p in pngs)


def test_diff_finds_most_changed_layer(files):
    text, pngs = w.diff(files / "before.safetensors", files / "after.pt", out=files / "rep")
    assert "изменились: 3" in text
    top2 = [l for l in text.splitlines() if l.startswith("| model.")][:2]
    assert "model.layers.0.self_attn.q_proj.weight" in top2[0]           # один вес 3.0 в матрице ~0.05
    assert "model.layers.2.mlp.up_proj.weight" in top2[1]                # весь слой сдвинут на 0.05
    assert "up_proj:" in text and len(pngs) == 2


def test_lora_matches_direct_svd(files):
    text, pngs = w.lora(files / "adapter", out=files / "rep")
    assert "Модулей с LoRA: 9 · r = 4 · alpha = 8" in text and "scale = alpha/r = 2" in text
    from safetensors.torch import load_file
    st = load_file(str(files / "adapter" / "adapter_model.safetensors"))
    k = "base_model.model.model.layers.0.mlp.up_proj"
    dw = st[k + ".lora_B.weight"] @ st[k + ".lora_A.weight"] * 2.0
    assert w._fmt(dw.norm().item()) in text                               # норма через QR = прямая
    assert text.index("up_proj:") < text.index("q_proj:")                 # up меняется сильнее
    assert len(pngs) == 2


def test_quant_block_beats_tensor_with_outlier(files):
    text, pngs = w.quant(files / "after.pt", out=files / "rep", bits=4)
    row = [l for l in text.splitlines() if l.startswith("| model.layers.0.self_attn.q_proj")][0]
    cells = [c.strip().rstrip("%") for c in row.split("|")[2:5]]
    tensor_err, row_err, block_err = map(float, cells)
    # выброс портит один общий масштаб; строки (16) и блоки (32 = 2 строки) страдают меньше
    assert row_err < tensor_err and block_err < tensor_err
    assert Path(pngs[0]).exists()


def test_mcp_server_roundtrip(files):
    p = subprocess.Popen([sys.executable, str(HERE / "mcp_server.py")], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True)
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "weights_diff", "arguments": {"before": str(files / "before.safetensors"),
                                                      "after": str(files / "after.pt"), "out": str(files / "m")}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
                "name": "weights_lora", "arguments": {"path": str(files / "nope")}}}]
    out, _ = p.communicate("\n".join(json.dumps(m) for m in msgs) + "\n", timeout=120)
    replies = {r["id"]: r for r in map(json.loads, out.splitlines())}
    assert replies[1]["result"]["serverInfo"]["name"] == "weights"
    assert {t["name"] for t in replies[2]["result"]["tools"]} >= {"weights_diff", "weights_lora"}
    text = replies[3]["result"]["content"][0]["text"]
    assert "model.layers.2.mlp.up_proj.weight" in text and "diff_top.png" in text
    assert replies[4]["result"]["isError"] is True
