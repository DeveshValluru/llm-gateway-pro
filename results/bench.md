# Benchmark results

- Target: `http://localhost:8000/v1/chat/completions`
- Model: `pirate`
- `max_tokens`: 100
- Requests per concurrency level: 24

## Non-streaming

| concurrency | requests | QPS | p50 (s) | p95 (s) | p99 (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 24 | 0.16 | 6.32 | 7.36 | 7.54 |
| 4 | 24 | 0.57 | 7.23 | 7.46 | 7.50 |
| 8 | 24 | 1.23 | 6.53 | 7.08 | 7.08 |
| 16 | 24 | 1.42 | 11.02 | 11.12 | 11.13 |

## Streaming (with TTFT)

| concurrency | requests | QPS | p50 (s) | p95 (s) | p99 (s) | TTFT p50 (s) | TTFT p95 (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 24 | 0.19 | 5.18 | 5.45 | 5.48 | 0.13 | 0.14 |
| 4 | 24 | 0.66 | 5.98 | 6.97 | 7.00 | 0.23 | 0.31 |
| 8 | 24 | 1.48 | 5.24 | 5.93 | 5.94 | 0.24 | 0.29 |
| 16 | 24 | 2.05 | 6.03 | 6.13 | 6.13 | 0.45 | 0.45 |
