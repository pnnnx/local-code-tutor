# Снимок my-coder-v4-Q4_K_M.gguf

sha256: `a5ab2658375bdf4aed925052c87f1241c03554feae2893baf77a13cf7af5d832`
размер: 4.36 GiB
тензоров: 339 · параметров: 7 615 616 512
выборка: до 128 строк на тензор (равномерно)

| ключ | значение |
|---|---|
| general.name | My Coder v4 |
| general.architecture | qwen2 |
| general.file_type | 15 |
| qwen2.context_length | 32768 |
| qwen2.block_count | 28 |
| qwen2.embedding_length | 3584 |
| chat_template_sha256 | 93ece0037c37d080 |
| chat_template_has_tools | True |

Параметры по типу хранения:
| тип | параметров | доля |
|---|---|---|
| Q4_K | 6 094 061 568 | 80.0% |
| Q6_K | 1 521 221 632 | 20.0% |
| F32 | 333 312 | 0.0% |

Самые «хвостатые» тензоры (|max|/σ):
| тензор | тип | RMS | |max|/σ | >6σ |
|---|---|---|---|---|
| blk.12.ffn_down.weight | Q4_K | 0.01877 | 45.9 | 0.007% |
| blk.0.ffn_gate.weight | Q4_K | 0.01685 | 43.4 | 0.028% |
| blk.14.ffn_down.weight | Q6_K | 0.01868 | 38.7 | 0.009% |
| blk.27.ffn_norm.weight | F32 | 1.746 | 37.0 | 0.363% |
| blk.5.ffn_norm.weight | F32 | 1.059 | 32.9 | 0.279% |
| blk.26.ffn_norm.weight | F32 | 1.389 | 31.7 | 0.307% |
| blk.5.ffn_up.weight | Q4_K | 0.01824 | 31.5 | 0.004% |
| blk.5.ffn_down.weight | Q6_K | 0.01806 | 28.5 | 0.005% |
| blk.27.ffn_down.weight | Q6_K | 0.01894 | 27.6 | 0.006% |
| blk.6.ffn_norm.weight | F32 | 0.5781 | 26.6 | 0.195% |

Графики:
- results/v4/snapshot/snapshot_rms.png
- results/v4/snapshot/snapshot_tails.png
- results/v4/snapshot/snapshot_types.png
- results/v4/snapshot/snapshot.json
