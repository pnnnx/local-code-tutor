# Шаблон ролика

`video.html` — canvas-таймлайн 10 с (1080×1920): крючок → «запускает код» → туннель из 3 карточек → карточка репо.
Все тексты — из `window.DATA` (`data.js` пишет `promo/build.py` из `base.json` + `releases/<версия>.json`).
`audio.py` — музыка и звук (синтез, 120 BPM; акценты совпадают с таймлайном). Шрифты — в `fonts/` (Inter — OFL-1.1,
DejaVu Sans Mono — лицензия Bitstream Vera/DejaVu, тексты лицензий рядом). Lo — `lo_assets.js` (из `scripts/brand/lo.py`).
Собирать: `./promo/build.sh v0.4.0` (или `--probe` — 6 кадров для проверки).
