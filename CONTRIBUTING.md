# Contributing

Thanks for looking! The most valuable contributions are **verified**: anything that can be checked by
running code is checked by running code.

## Good first contributions
- **New examples** for an existing category — see `ds/README.md`. Every example must run and its stated
  output must match the real one; `./ds.sh add your_batch.py` will tell you.
- **Held-out questions** with key-fact checks (`ds/eval_set.py`, `CHECKS`). The correct values must be
  obtained by running the code, not from memory.
- **Small-model failure modes** you have seen in an agent — open an issue with the exact prompt, model,
  quantization and the transcript. Fixes in [loca](https://github.com/pnnnx/loca) come with a probe.
- **wtools**: new analyses with a test on the toy model in `wtools/test_weights.py`.

## Development
```bash
pip install torch safetensors matplotlib numpy pandas pytest
python -m pytest -q wtools/test_weights.py
python -m py_compile ds/tools/*.py
```

## Pull requests
- One topic per PR, with a short **What / How / Why / How it was checked** in the description
  (the same structure as the commit messages and `docs/JOURNAL.md`).
- Don't add generated training data from models whose terms forbid training on their outputs.
- Be kind — see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
