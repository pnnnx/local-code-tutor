#!/bin/sh
# ./promo/build.sh v0.4.0 [--probe] — ролик к релизу (см. promo/build.py)
cd "$(dirname "$0")/.." && exec python3 promo/build.py "$@"
