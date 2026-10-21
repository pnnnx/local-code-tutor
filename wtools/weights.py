"""Анализ весов нейросети: таблицы + PNG-графики. CLI и библиотека (её же зовёт MCP-сервер для loca).

  python3 weights.py inspect model.safetensors            # что внутри: слои, формы, память
  python3 weights.py stats   model.pt [--tensor NAME]     # статистика по слоям, выбросы, гистограмма
  python3 weights.py diff    before.pt after.pt           # что изменилось после дообучения
  python3 weights.py lora    adapter_dir/                 # LoRA: ΔW = B·A·alpha/r, ранг, спектр
  python3 weights.py quant   model.pt [--bits 4]          # ошибка int8/int4: на тензор / на строку / блоками
  python3 weights.py snapshot model.gguf [--rows 256]     # снимок: sha256, метаданные, типы, статистика (и GGUF)

Форматы: .gguf (только snapshot; нужен `pip install gguf`), .safetensors, .pt/.pth/.bin (torch.load(weights_only=True)), папка адаптера PEFT
(adapter_model.safetensors|bin + adapter_config.json). Графики — в --out (по умолчанию ./weights_report).
Текст отчёта содержит все числа, нарисованные на графиках: модель в loca графики не видит,
но может объяснить их по числам.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path

import torch

# ---------------------------------------------------------------- оформление графиков
# Стиль как у витрины (scripts/brand): белая карточка со скруглением, пастельная заливка под линиями,
# палитра бренда. Подписи — по-русски; WTOOLS_LANG=en — по-английски (для README и англоязычных пользователей).
SERIES = ["#2a78d6", "#d0632a", "#23855c", "#7a4fd0", "#c8456a", "#a87a00", "#0f8b8d"]
SURFACE, INK, MUTED, GRID = "#ffffff", "#2b2f3a", "#6b7280", "#e9ecf2"
LANG = os.environ.get("WTOOLS_LANG", "ru")
W, H = 8.5, 3.4          # все графики одной ширины и высоты: рядом в отчёте и в README выглядят как набор


def _t(ru: str, en: str) -> str:
    return en if LANG == "en" else ru


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    fonts = {f.name for f in font_manager.fontManager.ttflist}
    family = next((f for f in ("Inter", "SF Pro Text", "Helvetica Neue", "Arial") if f in fonts), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": family, "font.size": 9.5,
        "figure.facecolor": "none", "axes.facecolor": "none", "savefig.facecolor": "none",
        "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
        "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.9, "grid.linestyle": (0, (4, 3)),
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 6, "ytick.major.pad": 6,
        "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 14,
        "axes.titlecolor": INK, "axes.labelsize": 9, "axes.labelpad": 8, "legend.frameon": False,
        "axes.prop_cycle": matplotlib.cycler(color=SERIES), "axes.axisbelow": True,
    })
    return plt


def _line(ax, xs, ys, color=SERIES[0], label=None, fill=True) -> None:
    """Линия с мягкой заливкой (если она одна на графике) и точками с белой обводкой."""
    if fill:
        ax.fill_between(xs, ys, 0, color=color, alpha=0.10, linewidth=0)
    ax.plot(xs, ys, color=color, linewidth=2.2, marker="o", markersize=4, markeredgecolor="white",
            markeredgewidth=1, label=label, solid_capstyle="round")


def _save(fig, out: Path, name: str) -> str:
    from matplotlib.patches import FancyBboxPatch
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    fig.tight_layout(pad=1.6)
    fig.patches.append(FancyBboxPatch((0.004, 0.006), 0.992, 0.988, boxstyle="round,pad=0,rounding_size=0.035",
                                      transform=fig.transFigure, facecolor=SURFACE, edgecolor="#e6e8ef",
                                      linewidth=1, zorder=-10, mutation_aspect=fig.get_figwidth() / fig.get_figheight()))
    fig.savefig(path, dpi=200, transparent=True)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return str(path)


def _depth_axis(ax, names: list[str], values: list[float] | None = None, fmt=lambda v: f"{v:.3g}") -> None:
    """Подписи по номерам слоёв вместо индексов тензоров + подпись максимума (одна, не на каждой точке)."""
    pos, labels, last = [], [], None
    for i, n in enumerate(names):
        m = re.search(r"\.(\d+)\.", "." + n + ".")
        layer = m.group(1) if m else None
        if layer is not None and layer != last:
            pos.append(i)
            labels.append(f"L{layer}")
        last = layer
    if pos:
        step = max(1, len(pos) // 12)
        ax.set_xticks(pos[::step], labels[::step])
        ax.set_xlabel(_t("слой модели (точка — одна матрица весов)", "layer (one dot = one weight matrix)"))
    if values:
        i = max(range(len(values)), key=lambda k: values[k])
        ax.annotate(f"{compact(names[i])}: {fmt(values[i])}", (i, values[i]), xytext=(6, 4),
                    textcoords="offset points", fontsize=8.5, color=INK, fontweight="bold")
        ax.set_ylim(0, max(values) * 1.18 or 1)


def _short(name: str, n: int = 38) -> str:
    return name if len(name) <= n else "…" + name[-(n - 1):]


# ---------------------------------------------------------------- загрузка
def load_state(path: str | Path) -> dict[str, torch.Tensor]:
    p = Path(path).expanduser()
    if p.is_dir():
        for cand in ("adapter_model.safetensors", "model.safetensors", "adapter_model.bin",
                     "pytorch_model.bin"):
            if (p / cand).exists():
                p = p / cand
                break
        else:
            raise SystemExit(f"В папке {p} нет *.safetensors / *.bin с весами")
    if p.suffix == ".safetensors":
        from safetensors.torch import load_file
        state = load_file(str(p))
    elif p.suffix == ".gguf":
        raise SystemExit("GGUF пока не поддерживается: анализируйте исходные safetensors / адаптер LoRA")
    else:
        state = torch.load(str(p), map_location="cpu", weights_only=True)
        for key in ("state_dict", "model", "model_state_dict"):
            if isinstance(state, dict) and key in state and isinstance(state[key], dict):
                state = state[key]
    if not isinstance(state, dict):
        raise SystemExit(f"{p}: ожидался словарь тензоров (state_dict), а не {type(state).__name__}")
    return {k: v for k, v in state.items() if isinstance(v, torch.Tensor)}


def _float(t: torch.Tensor) -> torch.Tensor:
    return t.detach().to(torch.float32)


def _group(name: str, depth: int = 2) -> str:
    parts = name.split(".")
    # model.layers.12.mlp.up_proj.weight → model.layers.12 ; fc1.weight → fc1
    for i, part in enumerate(parts):
        if part.isdigit():
            return ".".join(parts[: i + 1])
    return ".".join(parts[:depth]) if len(parts) > depth else parts[0]


def _natkey(name: str):
    """Порядок модели: эмбеддинги, слои по номеру (2 < 10), голова в конце."""
    first = 0 if "embed" in name else 2 if ("lm_head" in name or name.startswith(("norm", "model.norm"))) else 1
    return (first, [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)])


def ordered(names) -> list[str]:
    return sorted(names, key=_natkey)


def compact(name: str) -> str:
    """model.layers.12.self_attn.q_proj.weight → L12.q_proj; lm_head.weight → lm_head."""
    m = re.search(r"\.(\d+)\.", "." + name + ".")
    kind = _kind(name)
    return f"L{m.group(1)}.{kind}" if m else kind


def _fmt(x: float) -> str:
    if x == 0:
        return "0"
    a = abs(x)
    if a >= 1e4 or a < 1e-3:
        return f"{x:.2e}"
    return f"{x:.4g}"


def _table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


# ---------------------------------------------------------------- inspect
def inspect(path, out="weights_report", top: int = 40) -> tuple[str, list[str]]:
    state = load_state(path)
    total = sum(t.numel() for t in state.values())
    by_dtype: dict[str, int] = {}
    groups: dict[str, int] = {}
    for name, t in state.items():
        by_dtype[str(t.dtype).replace("torch.", "")] = by_dtype.get(str(t.dtype).replace("torch.", ""), 0) + t.numel()
        groups[_group(name)] = groups.get(_group(name), 0) + t.numel()
    rows = [[_short(n, 50), "×".join(map(str, t.shape)) or "скаляр", str(t.dtype).replace("torch.", ""),
             f"{t.numel():,}".replace(",", " "), f"{t.numel() * t.element_size() / 2**20:.2f}"]
            for n, t in list(state.items())[:top]]
    mem = {b: total * b / 8 / 2**30 for b in (32, 16, 8, 4)}
    text = [f"# Модель: {path}", f"Тензоров: {len(state)} · параметров: {total:,}".replace(",", " "),
            "Типы: " + ", ".join(f"{k} — {v:,}".replace(",", " ") for k, v in by_dtype.items()),
            "Память только на веса: " + " · ".join(f"{'fp' if b >= 16 else 'int'}{b}: {mem[b]:.2f} ГБ" for b in mem),
            "", f"Тензоры (первые {min(top, len(state))} из {len(state)}):", _table(["имя", "форма", "dtype", "параметров", "МБ"], rows)]
    top_groups = sorted(groups.items(), key=lambda kv: -kv[1])[:15]
    text += ["", "Крупнейшие блоки (доля параметров):",
             _table(["блок", "параметров", "доля"],
                    [[g, f"{n:,}".replace(",", " "), f"{100 * n / total:.1f}%"] for g, n in top_groups])]
    plt = _plt()
    fig, ax = plt.subplots(figsize=(W, 0.32 * len(top_groups) + 1.4))
    labels = [_short(g, 34) for g, _ in top_groups][::-1]
    vals = [100 * n / total for _, n in top_groups][::-1]
    ax.barh(labels, vals, color=SERIES[0], height=0.62, alpha=0.9)
    ax.set_xlabel(_t("доля параметров, %", "share of parameters, %"))
    ax.set_title(_t("Где лежат параметры модели", "Where the parameters live"))
    ax.grid(axis="y", visible=False)
    for y, v in enumerate(vals):
        ax.text(v, y, f" {v:.1f}%", va="center", color=MUTED, fontsize=8)
    png = _save(fig, Path(out), "inspect_blocks.png")
    return "\n".join(text), [png]


# ---------------------------------------------------------------- stats
def tensor_stats(t: torch.Tensor) -> dict:
    x = _float(t).flatten()
    n = x.numel()
    mean, std = x.mean().item(), x.std().item() if n > 1 else 0.0
    out = {"numel": n, "mean": mean, "std": std, "absmax": x.abs().max().item(),
           "rms": x.pow(2).mean().sqrt().item(), "l2": x.norm().item(),
           "near_zero": (x.abs() < 1e-6).float().mean().item(),
           "outliers": int(((x - mean).abs() > 6 * std).sum().item()) if std > 0 else 0}
    if t.dim() == 2 and t.shape[0] > 1:
        rows = _float(t).norm(dim=1)
        out["dead_rows"] = int((rows < 1e-8).sum().item())
    return out


def stats(path, out="weights_report", tensor: str | None = None, top: int = 30) -> tuple[str, list[str]]:
    state = {k: v for k, v in load_state(path).items() if v.is_floating_point() and v.numel() > 1}
    names = ordered(state)
    st = {n: tensor_stats(state[n]) for n in names}
    order = sorted(names, key=lambda n: -st[n]["rms"])
    rows = [[_short(n, 46), _fmt(st[n]["mean"]), _fmt(st[n]["std"]), _fmt(st[n]["rms"]), _fmt(st[n]["absmax"]),
             f"{100 * st[n]['near_zero']:.1f}%", st[n]["outliers"], st[n].get("dead_rows", "—")]
            for n in order[:top]]
    flags = []
    for n in names:
        s = st[n]
        if s["outliers"]:
            flags.append(f"- {n}: {s['outliers']} выбросов дальше 6σ (|max| = {_fmt(s['absmax'])}, σ = {_fmt(s['std'])}) — "
                         "такие тензоры сильнее всего страдают при квантовании per-tensor")
        if s.get("dead_rows"):
            flags.append(f"- {n}: {s['dead_rows']} нулевых строк — «мёртвые» нейроны")
        if s["near_zero"] > 0.5:
            flags.append(f"- {n}: {100 * s['near_zero']:.0f}% значений ≈ 0 — тензор разрежен")
    text = [f"# Статистика весов: {path}", f"Тензоров с плавающей точкой: {len(names)}",
            f"Сортировка по RMS (типичный размер веса), первые {min(top, len(names))}:",
            _table(["тензор", "mean", "std", "RMS", "|max|", "≈0", "выбросы>6σ", "нулевых строк"], rows),
            "", "Что бросается в глаза:", *(flags[:25] or ["- ничего необычного: выбросов, нулевых строк и разреженности нет"])]
    pngs = []
    plt = _plt()
    # 1) RMS по тензорам в порядке модели: видно, как масштаб весов меняется по глубине
    weights = [n for n in names if state[n].dim() >= 2] or names
    fig, ax = plt.subplots(figsize=(W, H))
    rms = [st[n]["rms"] for n in weights]
    _line(ax, range(len(weights)), rms)
    ax.set_xlabel(_t("матрица весов в порядке модели", "weight matrix, in model order"))
    ax.set_ylabel(_t("RMS веса", "weight RMS"))
    ax.set_title(_t("Масштаб весов по глубине модели", "Weight scale across depth"))
    _depth_axis(ax, weights, rms, _fmt)
    pngs.append(_save(fig, Path(out), "stats_rms_by_layer.png"))
    text += ["", "График stats_rms_by_layer.png — RMS по матрицам в порядке модели:",
             ", ".join(f"{compact(n)}={_fmt(st[n]['rms'])}" for n in weights[:60])]
    # 2) гистограмма одного тензора (по умолчанию — с наибольшим |max|/σ, самый «хвостатый»)
    pick = tensor if tensor in state else max(names, key=lambda n: st[n]["absmax"] / (st[n]["std"] or 1))
    x = _float(state[pick]).flatten()
    if x.numel() > 2_000_000:
        x = x[torch.randperm(x.numel(), generator=torch.Generator().manual_seed(0))[:2_000_000]]
    fig, ax = plt.subplots(figsize=(W, H))
    ax.hist(x.numpy(), bins=120, color=SERIES[0], alpha=0.85, log=True, edgecolor="white", linewidth=0.3)
    s = st[pick]
    for k in (-6, 6):
        ax.axvline(s["mean"] + k * s["std"], color=MUTED, linewidth=1, linestyle="--")
    ax.set_title(_t("Распределение весов: ", "Weight distribution: ") + _short(pick, 50))
    ax.set_xlabel(_t("значение веса (пунктир — ±6σ)", "weight value (dashed: ±6σ)"))
    ax.set_ylabel(_t("сколько весов (лог. шкала)", "count (log scale)"))
    pngs.append(_save(fig, Path(out), "stats_hist.png"))
    q = torch.quantile(x, torch.tensor([0.001, 0.5, 0.999])).tolist() if x.numel() < 16_000_000 else [float("nan")] * 3
    text += ["", f"График stats_hist.png — гистограмма {pick}: mean={_fmt(s['mean'])}, σ={_fmt(s['std'])}, "
                 f"|max|={_fmt(s['absmax'])} ({s['absmax'] / (s['std'] or 1):.1f}σ), квантили 0.1%/50%/99.9%: "
                 + " / ".join(_fmt(v) for v in q)]
    return "\n".join(text), pngs


# ---------------------------------------------------------------- diff
def diff(path_a, path_b, out="weights_report", top: int = 20) -> tuple[str, list[str]]:
    a, b = load_state(path_a), load_state(path_b)
    common = [n for n in ordered(a) if n in b and a[n].shape == b[n].shape and a[n].is_floating_point()]
    reshaped = [n for n in a if n in b and a[n].shape != b[n].shape]
    only_a, only_b = [n for n in a if n not in b], [n for n in b if n not in a]
    res = []
    for n in common:
        x, y = _float(a[n]).flatten(), _float(b[n]).flatten()
        d = (y - x).norm().item()
        base = x.norm().item()
        cos = torch.nn.functional.cosine_similarity(x, y, dim=0).item() if base > 0 and y.norm() > 0 else float("nan")
        res.append((n, d, d / base if base > 0 else float("inf"), cos))
    changed = [r for r in res if r[1] > 0]
    order = sorted(changed, key=lambda r: -r[2])
    text = [f"# Сравнение: {path_a} → {path_b}",
            f"Общих тензоров: {len(common)} · изменились: {len(changed)} · без изменений: {len(common) - len(changed)}"]
    if reshaped:
        text.append(f"Форма поменялась: {', '.join(reshaped[:10])}")
    if only_a or only_b:
        text.append(f"Только в первом: {len(only_a)} · только во втором: {len(only_b)} "
                    f"(например: {', '.join((only_b or only_a)[:5])})")
    text += ["", "Метрики: ‖ΔW‖ — норма разницы; относительное изменение ‖ΔW‖/‖W‖ — главное, оно сравнимо "
                 "между слоями разного размера; cos — косинус между весами до и после (1.0 — направление не изменилось).",
             _table(["тензор", "‖ΔW‖", "‖ΔW‖/‖W‖", "cos"],
                    [[_short(n, 50), _fmt(d), f"{100 * r:.3f}%", f"{c:.6f}"] for n, d, r, c in order[:top]])]
    groups: dict[str, list[float]] = {}
    for n, d, r, c in changed:
        groups.setdefault(_kind(n), []).append(r)
    if groups:
        text += ["", "По типу модуля (среднее относительное изменение):",
                 ", ".join(f"{k}: {100 * sum(v) / len(v):.3f}% ({len(v)} шт.)"
                           for k, v in sorted(groups.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])))]
    pngs = []
    if changed:
        plt = _plt()
        shown = order[:top][::-1]
        fig, ax = plt.subplots(figsize=(W, 0.3 * len(shown) + 1.4))
        ax.barh([_short(n, 40) for n, *_ in shown], [100 * r for _, _, r, _ in shown], color=SERIES[0], height=0.62, alpha=0.9)
        ax.set_xlabel(_t("относительное изменение ‖ΔW‖/‖W‖, %", "relative change ‖ΔW‖/‖W‖, %"))
        ax.set_title(_t(f"Какие слои изменились сильнее всего (топ-{len(shown)})", f"Most changed layers (top {len(shown)})"))
        ax.grid(axis="y", visible=False)
        pngs.append(_save(fig, Path(out), "diff_top.png"))
        series = [r for r in res if a[r[0]].dim() >= 2] or res
        fig, ax = plt.subplots(figsize=(W, H))
        vals = [100 * r for _, _, r, _ in series]
        _line(ax, range(len(series)), vals)
        ax.set_xlabel(_t("матрица весов в порядке модели", "weight matrix, in model order"))
        ax.set_ylabel("‖ΔW‖/‖W‖, %")
        ax.set_title(_t("Что сдвинуло дообучение — по глубине модели", "What fine-tuning moved, across depth"))
        _depth_axis(ax, [n for n, *_ in series], vals, lambda v: f"{v:.2f}%")
        pngs.append(_save(fig, Path(out), "diff_by_depth.png"))
        text += ["", "График diff_by_depth.png — изменение по глубине (в %): "
                 + ", ".join(f"{compact(n)}={100 * r:.3f}" for n, _, r, _ in series[:80])]
    return "\n".join(text), pngs


def _kind(name: str) -> str:
    """Тип модуля трансформера по имени: q_proj, up_proj, lm_head, embed…"""
    parts = [p for p in name.split(".") if p not in ("weight", "bias", "default", "base_layer")
             and not p.isdigit() and not p.startswith("lora_")]
    return parts[-1] if parts else name


# ---------------------------------------------------------------- lora
def lora(path, out="weights_report", alpha: float | None = None, r: int | None = None,
         top: int = 25) -> tuple[str, list[str]]:
    p = Path(path).expanduser()
    state = load_state(p)
    cfg_path = (p if p.is_dir() else p.parent) / "adapter_config.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    rank = r or cfg.get("r")
    alpha = alpha or cfg.get("lora_alpha")
    pairs: dict[str, dict[str, torch.Tensor]] = {}
    for name, t in state.items():
        m = re.match(r"(.*)\.lora_([AB])(?:\.default)?(?:\.weight)?$", name)
        if m:
            pairs.setdefault(m.group(1), {})[m.group(2)] = t
    mods = {k: v for k, v in pairs.items() if "A" in v and "B" in v}
    if not mods:
        raise SystemExit("Не нашёл пар lora_A / lora_B: это точно адаптер LoRA (PEFT)?")
    rows, per_kind, spectra = [], {}, {}
    for name in ordered(mods):
        ab = mods[name]
        A, B = _float(ab["A"]), _float(ab["B"])            # A: r×in, B: out×r
        rr = A.shape[0]
        scale = (alpha / (rank or rr)) if alpha else 1.0
        # сингулярные числа ΔW = B·A через QR: r×r вместо out×in — быстро и для 7B
        qb, rb = torch.linalg.qr(B)
        qa, ra = torch.linalg.qr(A.T)
        s = torch.linalg.svdvals(rb @ ra.T) * scale
        fro = s.norm().item()
        pnorm = s / s.sum() if s.sum() > 0 else s
        eff = math.exp(-(pnorm[pnorm > 0] * pnorm[pnorm > 0].log()).sum().item()) if s.sum() > 0 else 0.0
        top1 = (s[0] ** 2 / (s ** 2).sum()).item() if fro > 0 else 0.0
        kind = _kind(name)
        rows.append((name, kind, tuple(B.shape[:1]) + tuple(A.shape[1:]), rr, fro, eff, top1))
        per_kind.setdefault(kind, []).append(fro)
        spectra.setdefault(kind, []).append((s / s[0]).tolist() if s[0] > 0 else s.tolist())
    order = sorted(rows, key=lambda x: -x[4])
    zero_b = sum(1 for x in rows if x[4] == 0)
    text = [f"# LoRA-адаптер: {path}",
            f"Модулей с LoRA: {len(rows)} · r = {rank or rows[0][3]} · alpha = {alpha if alpha else '— (масштаб 1)'}"
            + (f" · scale = alpha/r = {alpha / (rank or rows[0][3]):.3g}" if alpha else ""),
            "ΔW = B·A·scale — добавка к весу базовой модели. ‖ΔW‖ — насколько сильно адаптер меняет модуль; "
            "эффективный ранг — сколько направлений реально используется из r (exp энтропии сингулярных чисел); "
            "доля σ₁² — сколько «энергии» в главном направлении.",
            _table(["модуль", "тип", "форма ΔW", "r", "‖ΔW‖", "эфф. ранг", "доля σ₁²"],
                   [[_short(n, 44), k, "×".join(map(str, sh)), rr, _fmt(f), f"{e:.2f}", f"{100 * t:.0f}%"]
                    for n, k, sh, rr, f, e, t in order[:top]])]
    if zero_b:
        text.append(f"\n⚠ У {zero_b} модулей ΔW = 0 (B — нули): адаптер не обучался или это свежая инициализация.")
    text += ["", "По типу модуля (средняя ‖ΔW‖): " + ", ".join(
        f"{k}: {_fmt(sum(v) / len(v))} ({len(v)} шт.)" for k, v in sorted(per_kind.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])))]
    plt = _plt()
    pngs = []
    kinds = sorted(per_kind, key=lambda k: -sum(per_kind[k]) / len(per_kind[k]))
    color = {k: SERIES[i] if i < len(SERIES) else MUTED for i, k in enumerate(kinds)}
    fig, ax = plt.subplots(figsize=(W, H))
    for i, (n, k, *_rest) in enumerate(rows):
        ax.bar(i, _rest[2], color=color[k], width=0.78, alpha=0.9)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=color[k], label=k) for k in kinds[:len(SERIES)]]
              + ([Patch(color=MUTED, label=_t("другие", "other"))] if len(kinds) > len(SERIES) else []),
              frameon=False, fontsize=8.5, ncol=min(4, len(kinds)))
    ax.set_xlabel(_t("модуль в порядке модели", "module, in model order"))
    ax.set_ylabel("‖ΔW‖")
    _depth_axis(ax, [x[0] for x in rows])
    ax.set_xlabel(_t("слой (столбец — один модуль с LoRA)", "layer (one bar = one LoRA module)"))
    ax.set_ylim(0, max(x[4] for x in rows) * 1.3 or 1)          # место для легенды над столбцами
    ax.set_title(_t("Насколько адаптер меняет каждый модуль", "How much the adapter changes each module"))
    pngs.append(_save(fig, Path(out), "lora_norms.png"))
    fig, ax = plt.subplots(figsize=(W, H))
    for k in kinds[:len(SERIES)]:
        arr = torch.tensor([sp + [0.0] * (max(map(len, spectra[k])) - len(sp)) for sp in spectra[k]]).mean(0)
        _line(ax, range(1, len(arr) + 1), arr.tolist(), color=color[k], label=k, fill=False)
    ax.set_xlabel(_t("номер сингулярного числа", "singular value index"))
    ax.set_ylabel(_t("σᵢ / σ₁ (среднее по модулям)", "σᵢ / σ₁ (mean over modules)"))
    ax.set_ylim(0, 1.05)
    ax.set_title(_t("Спектр ΔW: сколько направлений использует адаптер", "ΔW spectrum: how many directions the adapter uses"))
    ax.legend(frameon=False, fontsize=8.5)
    pngs.append(_save(fig, Path(out), "lora_spectrum.png"))
    text += ["", "График lora_spectrum.png — средний нормированный спектр σᵢ/σ₁ по типам: " + "; ".join(
        f"{k}: " + ", ".join(f"{v:.2f}" for v in torch.tensor(
            [sp + [0.0] * (max(map(len, spectra[k])) - len(sp)) for sp in spectra[k]]).mean(0).tolist()[:8])
        for k in kinds[:len(SERIES)])]
    return "\n".join(text), pngs


# ---------------------------------------------------------------- quant
def _qdq(x: torch.Tensor, bits: int, mode: str, block: int = 32) -> torch.Tensor:
    """Симметричное квантование и обратно: per-tensor / per-row / блоками по `block` (идея Q4_0/Q8_0 в GGUF)."""
    qmax = 2 ** (bits - 1) - 1
    if mode == "tensor":
        s = x.abs().max().clamp(min=1e-12) / qmax
        return (x / s).round().clamp(-qmax - 1, qmax) * s
    if mode == "row":
        x2 = x.reshape(x.shape[0], -1)
        s = x2.abs().amax(dim=1, keepdim=True).clamp(min=1e-12) / qmax
        return ((x2 / s).round().clamp(-qmax - 1, qmax) * s).reshape(x.shape)
    flat = x.flatten()
    pad = (-flat.numel()) % block
    f = torch.cat([flat, flat.new_zeros(pad)]).reshape(-1, block)
    s = f.abs().amax(dim=1, keepdim=True).clamp(min=1e-12) / qmax
    return ((f / s).round().clamp(-qmax - 1, qmax) * s).flatten()[: flat.numel()].reshape(x.shape)


def quant(path, out="weights_report", bits: int = 4, top: int = 20) -> tuple[str, list[str]]:
    state = {k: v for k, v in load_state(path).items() if v.is_floating_point() and v.dim() >= 2}
    res = []
    for n in ordered(state):
        t = state[n]
        x = _float(t)
        norm = x.norm().item() or 1.0
        errs = {m: ((_qdq(x, bits, m) - x).norm().item() / norm) for m in ("tensor", "row", "block")}
        st = tensor_stats(t)
        res.append((n, errs, st["absmax"] / (st["std"] or 1)))
    order = sorted(res, key=lambda r: -r[1]["tensor"])
    mean = {m: sum(r[1][m] for r in res) / len(res) for m in ("tensor", "row", "block")} if res else {}
    text = [f"# Квантование int{bits}: {path}",
            "Относительная ошибка ‖W − deq(q(W))‖/‖W‖ для трёх способов выбрать масштаб: один на тензор, "
            "свой на каждую строку, свой на каждый блок из 32 весов (так делают форматы GGUF Q4_0/Q8_0). "
            "Чем мельче группа, тем меньше вредит один выброс.",
            "Среднее по матрицам: " + " · ".join(f"{m}: {100 * v:.2f}%" for m, v in mean.items()),
            "", f"Хуже всего переносят квантование (по per-tensor), первые {min(top, len(order))}:",
            _table(["тензор", "per-tensor", "per-row", "блоки 32", "|max|/σ"],
                   [[_short(n, 46), f"{100 * e['tensor']:.2f}%", f"{100 * e['row']:.2f}%", f"{100 * e['block']:.2f}%",
                     f"{k:.1f}"] for n, e, k in order[:top]])]
    pngs = []
    if res:
        plt = _plt()
        fig, ax = plt.subplots(figsize=(W, H))
        labels = {"tensor": _t("один масштаб на тензор", "one scale per tensor"), "row": _t("на строку", "per row"), "block": _t("блоки по 32", "32-blocks")}
        for i, m in enumerate(("tensor", "row", "block")):
            _line(ax, range(len(res)), [100 * r[1][m] for r in res], color=SERIES[i], label=labels[m], fill=False)
        ax.set_xlabel(_t("матрица весов в порядке модели", "weight matrix, in model order"))
        ax.set_ylabel(_t("относительная ошибка, %", "relative error, %"))
        _depth_axis(ax, [r[0] for r in res], [100 * r[1]["tensor"] for r in res], lambda v: f"{v:.1f}%")
        ax.set_title(_t(f"Ошибка int{bits} по слоям", f"int{bits} error per layer"))
        ax.legend(frameon=False, fontsize=8)
        pngs.append(_save(fig, Path(out), f"quant_int{bits}.png"))
    return "\n".join(text), pngs


# ---------------------------------------------------------------- CLI


# ---------------------------------------------------------------- снимок модели (в т.ч. GGUF)
GGUF_KIND = re.compile(r"(attn_q|attn_k|attn_v|attn_output|ffn_gate|ffn_up|ffn_down|q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)")


def _sha256(path: Path, chunk: int = 1 << 24) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def _gguf_tensors(path: Path, rows: int):
    """GGUF без загрузки целиком: метаданные + по каждому тензору выборка строк (деквантованная)."""
    import gguf
    import numpy as np
    r = gguf.GGUFReader(str(path))
    meta = {}
    for k, f in r.fields.items():
        if k.startswith("GGUF.") or k.startswith("tokenizer.ggml."):
            continue
        try:
            v = f.contents()
        except Exception:  # noqa: BLE001
            continue
        if k == "tokenizer.chat_template":
            import hashlib
            meta["chat_template_sha256"] = hashlib.sha256(str(v).encode()).hexdigest()[:16]
            meta["chat_template_has_tools"] = "tools" in str(v)
            continue
        meta[k] = v if isinstance(v, (int, float, str, bool)) else str(v)[:120]
    out = []
    for t in r.tensors:
        shape = [int(x) for x in reversed(t.shape.tolist())]           # как в PyTorch: [out, in]
        data = t.data
        n_rows = data.shape[0] if data.ndim > 1 else 1
        take = np.linspace(0, n_rows - 1, min(rows, n_rows)).astype(int) if n_rows > 1 else None
        part = data[take] if take is not None else data
        x = gguf.quants.dequantize(np.asarray(part), t.tensor_type).astype(np.float32).ravel()
        out.append((t.name, shape, t.tensor_type.name, int(t.n_elements), x, len(take) if take is not None else 1, n_rows))
    return meta, out


def snapshot(path, out="weights_report", rows: int = 256) -> tuple[str, list[str]]:
    """Снимок модели: sha256, метаданные, типы квантования и статистика каждого тензора по выборке строк.
    Работает с GGUF (без загрузки всей модели в память) и с safetensors/.pt. Пишет snapshot.json рядом с графиками."""
    import numpy as np
    path, out = Path(path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    info = {"file": path.name, "bytes": path.stat().st_size if path.is_file() else None,
            "sha256": _sha256(path) if path.is_file() else None, "rows_per_tensor": rows}
    if path.suffix == ".gguf":
        meta, items = _gguf_tensors(path, rows)
    else:
        meta, items = {}, []
        for n, t in load_state(path).items():
            x = _float(t)
            n_rows = x.shape[0] if x.dim() > 1 else 1
            idx = torch.linspace(0, n_rows - 1, min(rows, n_rows)).long() if n_rows > 1 else None
            part = (x[idx] if idx is not None else x).flatten().numpy()
            items.append((n, list(t.shape), str(t.dtype).replace("torch.", ""), t.numel(), part,
                          len(idx) if idx is not None else 1, n_rows))
    info["meta"] = meta
    tensors, by_type = [], {}
    for name, shape, qtype, numel, x, took, n_rows in items:
        sd = float(x.std()) if x.size > 1 else 0.0
        mean = float(x.mean()) if x.size else 0.0
        amax = float(np.abs(x).max()) if x.size else 0.0
        out6 = float((np.abs(x - mean) > 6 * sd).mean()) if sd > 0 else 0.0
        tensors.append({"name": name, "shape": shape, "type": qtype, "params": numel, "rows_sampled": f"{took}/{n_rows}",
                        "mean": mean, "std": sd, "rms": float(np.sqrt((x.astype(np.float64) ** 2).mean())) if x.size else 0.0,
                        "absmax": amax, "tail": amax / sd if sd else 0.0, "outliers_6sigma": out6})
        by_type[qtype] = by_type.get(qtype, 0) + numel
    total = sum(t["params"] for t in tensors)
    info.update(params=total, tensors=len(tensors), params_by_type=by_type, stats=tensors)
    (out / "snapshot.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))

    lines = [f"# {_t('Снимок', 'Snapshot')} {path.name}", "",
             f"sha256: `{info['sha256']}`" if info["sha256"] else "",
             f"{_t('размер', 'size')}: {info['bytes'] / 2**30:.2f} GiB" if info["bytes"] else "",
             f"{_t('тензоров', 'tensors')}: {len(tensors)} · {_t('параметров', 'parameters')}: {total:,}".replace(",", " "),
             f"{_t('выборка', 'sample')}: {_t('до', 'up to')} {rows} {_t('строк на тензор (равномерно)', 'rows per tensor (evenly spaced)')}", ""]
    keys = [k for k in ("general.name", "general.architecture", "general.file_type", "qwen2.context_length",
                        "qwen2.block_count", "qwen2.embedding_length", "chat_template_sha256", "chat_template_has_tools") if k in meta]
    if keys:
        lines += [_table([_t("ключ", "key"), _t("значение", "value")], [[k, meta[k]] for k in keys]), ""]
    lines += [_t("Параметры по типу хранения:", "Parameters by storage type:"),
              _table([_t("тип", "type"), _t("параметров", "params"), _t("доля", "share")],
                     [[k, f"{v:,}".replace(",", " "), f"{100 * v / total:.1f}%"] for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])]), ""]
    worst = sorted(tensors, key=lambda t: -t["tail"])[:10]
    lines += [_t("Самые «хвостатые» тензоры (|max|/σ):", "Heaviest tails (|max|/σ):"),
              _table([_t("тензор", "tensor"), _t("тип", "type"), "RMS", "|max|/σ", ">6σ"],
                     [[_short(t["name"], 40), t["type"], _fmt(t["rms"]), f"{t['tail']:.1f}", f"{100 * t['outliers_6sigma']:.3f}%"] for t in worst])]

    plt = _plt()
    pngs = []
    mats = [t for t in tensors if len(t["shape"]) >= 2 and GGUF_KIND.search(t["name"])]
    if mats:
        kinds = []
        for t in mats:
            k = GGUF_KIND.search(t["name"]).group(1)
            if k not in kinds:
                kinds.append(k)
        fig, ax = plt.subplots(figsize=(W, H + 0.6))
        for i, k in enumerate(kinds[:len(SERIES)]):
            pts = [(int(m.group(1)), t["rms"]) for t in mats if GGUF_KIND.search(t["name"]).group(1) == k
                   for m in [re.search(r"(?:blk|layers)\.(\d+)\.", t["name"])] if m]
            if pts:
                pts.sort()
                _line(ax, [p[0] for p in pts], [p[1] for p in pts], color=SERIES[i], label=k, fill=False)
        ax.set_xlabel(_t("номер слоя", "layer"))
        ax.set_ylabel(_t("RMS веса", "weight RMS"))
        ax.set_title(_t("Масштаб весов по слоям и типам матриц", "Weight scale by layer and matrix type"))
        ax.legend(ncol=min(7, len(kinds)), fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2))
        pngs.append(_save(fig, out, "snapshot_rms.png"))
        fig, ax = plt.subplots(figsize=(W, H))
        xs = list(range(len(mats)))
        _line(ax, xs, [t["tail"] for t in mats], color=SERIES[3])
        ax.set_ylabel("|max| / σ")
        ax.set_title(_t("«Хвосты» распределений: где живут выбросы", "Distribution tails: where the outliers live"))
        _depth_axis(ax, [t["name"].replace("blk.", "layers.") for t in mats], [t["tail"] for t in mats], lambda v: f"{v:.0f}σ")
        pngs.append(_save(fig, out, "snapshot_tails.png"))
    fig, ax = plt.subplots(figsize=(W, 0.42 * len(by_type) + 1.5))
    order = sorted(by_type.items(), key=lambda kv: kv[1])
    ax.barh([k for k, _ in order], [100 * v / total for _, v in order], color=SERIES[0], height=0.6, alpha=0.9)
    for y, (_, v) in enumerate(order):
        ax.text(100 * v / total, y, f"  {100 * v / total:.1f}%", va="center", color=MUTED, fontsize=8.5)
    ax.set_xlabel(_t("доля параметров, %", "share of parameters, %"))
    ax.set_title(_t("Как хранятся веса (типы квантования)", "How weights are stored (quant types)"))
    ax.grid(axis="y", visible=False)
    pngs.append(_save(fig, out, "snapshot_types.png"))
    return "\n".join(l for l in lines if l is not None), pngs + [str(out / "snapshot.json")]


COMMANDS = {"inspect": inspect, "stats": stats, "diff": diff, "lora": lora, "quant": quant, "snapshot": snapshot}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", default="weights_report")
    ap.add_argument("--tensor")
    ap.add_argument("--bits", type=int, default=4)
    ap.add_argument("--top", type=int)
    ap.add_argument("--rows", type=int, default=256, help="snapshot: строк на тензор в выборке")
    args = ap.parse_args(argv)
    kw = {"out": args.out}
    if args.top:
        kw["top"] = args.top
    if args.command == "diff":
        if len(args.paths) != 2:
            raise SystemExit("diff: нужны два файла — до и после")
        text, pngs = diff(args.paths[0], args.paths[1], **kw)
    elif args.command == "stats":
        text, pngs = stats(args.paths[0], tensor=args.tensor, **kw)
    elif args.command == "snapshot":
        text, pngs = snapshot(args.paths[0], out=args.out, rows=args.rows)
    elif args.command == "quant":
        text, pngs = quant(args.paths[0], bits=args.bits, **kw)
    else:
        text, pngs = COMMANDS[args.command](args.paths[0], **kw)
    print(text)
    if pngs:
        print("\nГрафики:\n" + "\n".join(f"- {p}" for p in pngs))


if __name__ == "__main__":
    main()
