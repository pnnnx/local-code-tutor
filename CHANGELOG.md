# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning: [SemVer](https://semver.org/). A detailed day-by-day log is in [docs/JOURNAL.md](docs/JOURNAL.md).

## [Unreleased]
### Added
- Java examples built around the author's university practice tasks (`ds/prompts/java_claude.md`).
- `./ds.sh claude` — one-file dataset batches generated in a Claude chat, mixed categories per batch.
### Changed
- Prompts ask for *trace-then-verdict* answers on "what will this print?" questions (v2 invented outputs).

## [0.3.0] — 2026-10-20
### Added
- **Model v3**: 954 verified examples (+pandas, SQLite analytics, PyTorch, weight analysis, first Java,
  persona mode) — **13/18** held-out key facts vs 8/18 for the base model and 9/15 for v2.
- Held-out set extended to 18 questions (PyTorch training bug, `eval()` vs `no_grad()`, `state_dict` diff).
- Persona mode switched on by a system-prompt line; no profanity leaks into normal answers.
### Fixed
- Agent plans stalled on the first subtask: a test *file name* in the acceptance check went to
  `unittest -k` (a test-*name* filter) → "Ran 0 tests" → rollback. Found on Qwen2.5-Coder-7B; file
  targets are now resolved on disk and run as files.

## [0.2.0] — 2026-10-20
### Added
- **Model v2**: QLoRA on Qwen2.5-Coder-7B-Instruct, 762 verified + 300 general examples, GGUF `Q4_K_M`.
- **Auto-scoring** of held-out answers (`ds/tools/score_eval.py`, key-fact regexes per question).
- **wtools**: `inspect`, `stats`, `diff`, `lora`, `quant` with PNG charts; MCP server for the agent.
- **Agent (loca)**: task spec with deterministic checks; auto-run of code before "what will this print?";
  repo map with signatures, per-file tests and caching; llama.cpp backend; probe harness for 7B failure modes.
- Automatic git commit for every accepted dataset batch, with rejection reasons in the message.
### Fixed
- Examples using `pip install --user` packages failed verification (`python -I` hid user site-packages).
- ChatGPT answers split into pieces by inner code fences — answers now use a 4-backtick outer fence.

## [0.1.0] — 2026-10-19
### Added
- Dataset pipeline: execution-verified examples (Python, JS, C/C++, Java, SQLite), skeleton dedup,
  held-out eval set (18 questions), coverage report.
- Model v1 (trial fine-tune) and Kaggle notebooks for training and agent benchmarking.
