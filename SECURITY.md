# Security policy

## What runs code
- `ds/tools/runner.py` **executes example code** (Python, Node, gcc/g++, javac, SQLite) in a temporary
  directory with a timeout. It is **not a sandbox**: only run batches you have looked at.
- The loca agent auto-runs code from a question before answering, but skips code that deletes or writes
  files, opens network connections, spawns processes, reads stdin or loops forever; every run goes through
  the agent's permission system.
- `wtools` loads checkpoints with `torch.load(weights_only=True)` or safetensors — no pickle execution.

## Reporting a vulnerability
Please don't open a public issue. Use GitHub's **private vulnerability reporting**
(Security → Report a vulnerability) on this repository. You'll get an answer within a week.
