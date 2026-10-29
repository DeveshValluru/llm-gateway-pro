"""Benchmark the gateway.

Measures:
- QPS at varying concurrency levels
- End-to-end request latency (p50 / p95 / p99)
- Time to first content token (TTFT), streaming only

Writes a Markdown table to stdout and to results/bench.md, suitable for
pasting into the README. Uses the dedicated "bench" user so the rate
limiter does not interfere with the measurement.

Run: python scripts/bench.py
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:8000/v1") + "/chat/completions"
API_KEY = os.environ.get("BENCH_API_KEY", "sk-bench-key")
MODEL = os.environ.get("BENCH_MODEL", "pirate")
MAX_TOKENS = int(os.environ.get("BENCH_MAX_TOKENS", "100"))
PROMPT = os.environ.get("BENCH_PROMPT", "Tell me a short story about the sea.")

CONCURRENCY_LEVELS = [1, 4, 8, 16]
REQUESTS_PER_LEVEL = 24


@dataclass
class Sample:
    total_s: float
    ttft_s: float | None  # None for non-streaming


async def one_request(client: httpx.AsyncClient, streaming: bool) -> Sample:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
        "stream": streaming,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}

    t0 = time.perf_counter()

    if not streaming:
        resp = await client.post(GATEWAY, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return Sample(total_s=time.perf_counter() - t0, ttft_s=None)

    first_token_at: float | None = None
    async with client.stream("POST", GATEWAY, headers=headers, json=payload, timeout=120) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: ") or line.endswith("[DONE]"):
                continue
            if first_token_at is not None:
                continue
            try:
                chunk = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if choices and choices[0].get("delta", {}).get("content"):
                first_token_at = time.perf_counter()
    return Sample(total_s=time.perf_counter() - t0, ttft_s=(first_token_at - t0) if first_token_at else None)


async def run_level(concurrency: int, n: int, streaming: bool) -> dict:
    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(concurrency)

        async def bounded() -> Sample:
            async with sem:
                return await one_request(client, streaming)

        wall_start = time.perf_counter()
        samples = await asyncio.gather(*[bounded() for _ in range(n)])
        wall = time.perf_counter() - wall_start

    totals = sorted(s.total_s for s in samples)
    ttfts = sorted(s.ttft_s for s in samples if s.ttft_s is not None)

    def pct(xs: list[float], p: float) -> float | None:
        if not xs:
            return None
        k = min(len(xs) - 1, int(round(p * (len(xs) - 1))))
        return xs[k]

    return {
        "concurrency": concurrency,
        "requests": n,
        "qps": n / wall,
        "p50_s": statistics.median(totals),
        "p95_s": pct(totals, 0.95),
        "p99_s": pct(totals, 0.99),
        "ttft_p50_s": statistics.median(ttfts) if ttfts else None,
        "ttft_p95_s": pct(ttfts, 0.95),
    }


def fmt(x: float | None, places: int = 2) -> str:
    return f"{x:.{places}f}" if x is not None else "—"


def render_table(rows: list[dict], streaming: bool) -> str:
    lines = []
    if streaming:
        lines.append("| concurrency | requests | QPS | p50 (s) | p95 (s) | p99 (s) | TTFT p50 (s) | TTFT p95 (s) |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in rows:
            lines.append(
                f"| {r['concurrency']} | {r['requests']} | {fmt(r['qps'])} | "
                f"{fmt(r['p50_s'])} | {fmt(r['p95_s'])} | {fmt(r['p99_s'])} | "
                f"{fmt(r['ttft_p50_s'])} | {fmt(r['ttft_p95_s'])} |"
            )
    else:
        lines.append("| concurrency | requests | QPS | p50 (s) | p95 (s) | p99 (s) |")
        lines.append("|---:|---:|---:|---:|---:|---:|")
        for r in rows:
            lines.append(
                f"| {r['concurrency']} | {r['requests']} | {fmt(r['qps'])} | "
                f"{fmt(r['p50_s'])} | {fmt(r['p95_s'])} | {fmt(r['p99_s'])} |"
            )
    return "\n".join(lines)


async def warmup():
    print("Warmup (3 requests)...", flush=True)
    async with httpx.AsyncClient() as client:
        for _ in range(3):
            await one_request(client, streaming=True)


async def main():
    await warmup()

    print(f"\nTarget: {GATEWAY}")
    print(f"Model: {MODEL}, max_tokens: {MAX_TOKENS}")
    print(f"Concurrency levels: {CONCURRENCY_LEVELS}, requests per level: {REQUESTS_PER_LEVEL}\n")

    non_streaming_rows = []
    print("--- non-streaming ---")
    for c in CONCURRENCY_LEVELS:
        row = await run_level(c, REQUESTS_PER_LEVEL, streaming=False)
        non_streaming_rows.append(row)
        print(f"c={c:>3} QPS={row['qps']:.2f} p50={row['p50_s']:.2f}s p95={row['p95_s']:.2f}s p99={row['p99_s']:.2f}s")

    streaming_rows = []
    print("\n--- streaming ---")
    for c in CONCURRENCY_LEVELS:
        row = await run_level(c, REQUESTS_PER_LEVEL, streaming=True)
        streaming_rows.append(row)
        print(
            f"c={c:>3} QPS={row['qps']:.2f} "
            f"p50={row['p50_s']:.2f}s p95={row['p95_s']:.2f}s p99={row['p99_s']:.2f}s "
            f"TTFT p50={row['ttft_p50_s']:.2f}s TTFT p95={row['ttft_p95_s']:.2f}s"
        )

    out = Path(__file__).resolve().parent.parent / "results" / "bench.md"
    out.parent.mkdir(exist_ok=True)
    md = (
        "# Benchmark results\n\n"
        f"- Target: `{GATEWAY}`\n"
        f"- Model: `{MODEL}`\n"
        f"- `max_tokens`: {MAX_TOKENS}\n"
        f"- Requests per concurrency level: {REQUESTS_PER_LEVEL}\n\n"
        "## Non-streaming\n\n"
        + render_table(non_streaming_rows, streaming=False)
        + "\n\n## Streaming (with TTFT)\n\n"
        + render_table(streaming_rows, streaming=True)
        + "\n"
    )
    out.write_text(md, encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
