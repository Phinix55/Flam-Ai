# Part B — Capacity reconciliation

*Model `FLM-4B-Instruct (dense)` on `1× NVIDIA L4 (24 GB)`. Commit `4260f931772d61db634ce4200543f4e26e29b6b9-dirty`.
Every value below is parsed from `bench/model_spec.md`; nothing is hardcoded.*

## B1 — KV bytes per token

| term | value |
|---|---|
| `k_and_v_factor` | 2 |
| `layers` | 28 |
| `kv_heads` | 8 |
| `head_dim` | 128 |
| `dtype_bytes` | 2 |
| `kv_dim_per_layer` | 1024 |
| `bytes_per_token` | 114688 |
| `group_ratio` | 3.0 |
| `mha_bytes_per_token` | 344064 |

## B1 — Concurrency ceiling at max_model_len

Both readings of the spec's memory figure are carried; the log selects between
them.

| term | binary_GiB | decimal_GB |
|---|---|---|
| `gpu_memory_bytes` | 25769803776 | 24000000000 |
| `usable_bytes` | 23708219473 | 22080000000 |
| `weights_bytes` | 8400000000 | 8400000000 |
| `runtime_overhead_bytes` | 1717986918 | 1600000000 |
| `kv_budget_bytes` | 13590232555 | 12080000000 |
| `bytes_per_sequence` | 469762048 | 469762048 |
| `kv_capacity_tokens` | 118497 | 105329 |
| `exact_sequences` | 28.9300 | 25.7151 |
| `max_concurrent_sequences` | 28 | 25 |

**Checked against the log.** Predicted ceiling 25.72 sequences
(floor 25). Preemption prediction matches every row of the
long-prompt sweep: `True`.

TODO(pratik): interpretation

## B2 — The long-context throughput anomaly

Throughput peaks at batch 24 (1607.4 tok/s) and
falls to 1384.0 tok/s at batch 32.

TODO(pratik): interpretation

## B3 — Goodput of the long-prompt row at batch 24

| derivation | columns used | counts | tok/s |
|---|---|---|---|
| output tokens / wall clock | `num_requests`, `gen_len`, `wall_clock_s` | generated only | 200.92 |
| batch size / median inter-token latency | `batch_size`, `itl_ms_p50` | generated only, decode phase | 249.82 |

The harness counter reconstructs as requests × (prompt + generated) / wall
clock to within 0.0219 % on every row of the log.

TODO(pratik): interpretation

## B4 — The confirming counter

TODO(pratik): interpretation
