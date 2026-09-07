# Part B — Capacity reconciliation

*Model `FLM-4B-Instruct (dense)` on `1× NVIDIA L4 (24 GB)`. Commit `fd3e481e89b59415a68867936ab60e0d233b0818-dirty`.
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

The spec's bare "GB" is ambiguous and the two readings differ by three
sequences, so both are carried and the log decides. Under the decimal reading
`preempted_seqs` equals `batch_size` minus 25 on every
saturated row; the binary reading predicts different values that the log does
not show. Independently, the unsaturated rows invert their `kv_cache_util` to a
KV capacity that matches the predicted 105329 tokens.
Two unrelated signals agree, so the ceiling is 25 concurrent
sequences at this context length — a hard memory bound, not a tuning
preference.

## B2 — The long-context throughput anomaly

Throughput peaks at batch 24 (1607.4 tok/s) and
falls to 1384.0 tok/s at batch 32.

Configuration changes whose effect is arithmetically predictable from the
spec. None is recommended here; the choice and its justification are the
answer to B2.

| change | what it alters | ceiling before | ceiling after | x |
|---|---|---|---|---|
| `cap_concurrency_at_ceiling` | admit at most 25 concurrent sequences | 25 | 25 | 1.00 |
| `halve_max_model_len` | max_model_len 4096 -> 2048 | 25 | 51 | 2.00 |
| `kv_cache_fp8` | KV cache precision fp16 -> fp8 | 25 | 51 | 2.00 |

## B3 — Goodput of the long-prompt row at batch 24

| derivation | columns used | counts | tok/s |
|---|---|---|---|
| output tokens / wall clock | `num_requests`, `gen_len`, `wall_clock_s` | generated only | 200.92 |
| batch size / median inter-token latency | `batch_size`, `itl_ms_p50` | generated only, decode phase | 249.82 |

The harness counter reconstructs as requests × (prompt + generated) / wall
clock to within 0.0219 % on every row of the log.

**The misread column is `reported_tok_s`.** It is not goodput: it counts prompt
tokens alongside generated ones. That identity holds across every row of the
log, so this is a property of the column rather than an inference about it.

**One misreading collapses both conclusions because both are read off that
numerator.** Prompt tokens are processed once in prefill, so counting them
inflates the figure in direct proportion to prompt length — at prompt
3584, 87.5 % of the counted tokens are prompt. The comparison
at equal batch size makes it explicit: short prompts report
883.2 tok/s against long prompts' 1311.4,
but output-only goodput is 294.5 tok/s for short against
163.9 for long. **The ordering reverses.** So conclusion one —
that longer prompts give better throughput — is an artifact of the numerator,
and conclusion two — that batch scales linearly to a target — extrapolates from
a "best observed" value that is already past the turn-over point, on a metric
that rises with prompt length whether or not the server is doing more useful
work.

**Honest goodput of that row: 200.92 tok/s** (generated tokens
over wall clock). Derived independently from the decode loop —
`batch_size` ÷ `itl_ms_p50` — gives 249.82 tok/s, the
decode-phase rate; the two reconcile through the 19.6 % of
the run spent outside decode. Both are far below the reported figure.

**What the report should have said:** at equal batch, longer prompts *reduce*
useful throughput; the server is bounded at 25 concurrent
4096-token sequences, so the batch-48 target
is unreachable on this hardware at this context length, and the sustainable operating point is the knee at batch
24.

## B4 — The confirming counter

**Pull the engine's total KV-cache block count and multiply by block size —
`num_gpu_blocks` × `block_size` in a vLLM-style stack — and expect it to show
approximately 105329 tokens of KV capacity.** That is the
single number B1 predicts from the model spec and the memory budget, and it
confirms the B2 mechanism at its root rather than through its symptoms: if
capacity is what it should be, then the turn-over at batch
24 follows arithmetically, since 25 ×
4096 is all the residency that fits. It is also the counter that discriminates
against the alternative explanation — if throughput were falling because of
compute saturation rather than memory, capacity would be as predicted while
`preempted_seqs` stayed at 0, which is not what the log shows.
