# wtools — анализ весов с графиками

Пять инструментов; каждый печатает таблицу со всеми числами и сохраняет PNG в `weights_report/`.

| команда | что показывает | графики |
|---|---|---|
| `inspect файл` | тензоры, формы, dtype, параметры, память fp32/fp16/int8/int4, крупнейшие блоки | доля параметров по блокам |
| `stats файл [--tensor имя]` | mean/std/RMS/\|max\| по слоям, выбросы > 6σ, нулевые строки, разреженность | RMS по глубине, гистограмма |
| `diff до после` | ‖ΔW‖, ‖ΔW‖/‖W‖, косинус по слоям и типам модулей | топ изменившихся, изменение по глубине |
| `lora папка_адаптера` | ΔW = B·A·alpha/r: норма, эффективный ранг, доля главного направления | ‖ΔW‖ по модулям, спектр |
| `quant файл [--bits 4]` | ошибка int8/int4: масштаб на тензор / строку / блок 32 (как GGUF) | ошибка по слоям |

```bash
python3 wtools/weights.py lora ~/Downloads/lora_adapter_v2          # что сделал наш адаптер v2
python3 wtools/weights.py diff base.safetensors merged.safetensors
```
Форматы: `.safetensors`, `.pt/.pth/.bin` (`torch.load(weights_only=True)`), папка адаптера PEFT.
GGUF пока не читается — анализируйте исходные веса или адаптер.

## В loca
```bash
python3 wtools/install_loca.py      # один раз: MCP-сервер weights в ~/.loca/config.json
```
Дальше в loca просто просите: «покажи, какие слои сильнее всего изменил адаптер в ~/Downloads/lora_adapter_v2» —
модель вызовет `mcp__weights__weights_lora`, получит таблицу и пути к графикам и объяснит по числам.

Тесты: `python3 -m pytest -q wtools/test_weights.py` (крошечная модель с именами как у Qwen).
