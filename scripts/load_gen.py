"""Generate sustained traffic against the gateway for dashboard screenshots.

Mixes:
- 3 personalities (shows up on "per model" charts)
- 2 valid users (alice, bob) + a bad-key hacker (shows up on "per user" + error panels)
- Occasional forbidden model attempts (403s)
- Occasional rate-limit floods on bob (429s)

Run: python load_gen.py [duration_seconds] [concurrency]
Defaults: 300 seconds, 4 concurrent workers.
"""

import asyncio
import random
import sys
import time
import httpx

GATEWAY = "http://localhost:8000/v1/chat/completions"

PROMPTS = [
    "Explain what a GPU is.",
    "Tell me about the ocean.",
    "What is machine learning?",
    "Describe a sunset.",
    "What do you think about coffee?",
    "Explain quantum computing.",
    "Tell me a joke.",
    "What is the meaning of life?",
    "Describe your favorite food.",
    "How does the internet work?",
]

USERS = [
    {"name": "alice", "key": "sk-alice-dev-key", "models": ["pirate", "genz", "formal"], "weight": 5},
    {"name": "bob",   "key": "sk-bob-dev-key",   "models": ["pirate"], "weight": 3},
]

ALL_MODELS = ["pirate", "genz", "formal"]


async def send_one(client: httpx.AsyncClient):
    """Fire one request with randomized shape to produce varied metrics."""
    r = random.random()

    if r < 0.05:
        # 5% bad API key -> 401
        key, model = "bad-key", random.choice(ALL_MODELS)
    elif r < 0.15:
        # 10% bob tries a forbidden personality -> 403
        key, model = "sk-bob-dev-key", random.choice(["genz", "formal"])
    else:
        # 85% legitimate traffic
        user = random.choices(USERS, weights=[u["weight"] for u in USERS])[0]
        key = user["key"]
        model = random.choice(user["models"])

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": random.choice(PROMPTS)}],
        "max_tokens": random.choice([40, 60, 100, 150]),
        "temperature": random.uniform(0.3, 1.0),
    }

    try:
        resp = await client.post(
            GATEWAY,
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=60.0,
        )
        return resp.status_code
    except Exception as e:
        return f"ERR:{type(e).__name__}"


async def worker(client: httpx.AsyncClient, stop_at: float, stats: dict):
    while time.time() < stop_at:
        status = await send_one(client)
        stats[str(status)] = stats.get(str(status), 0) + 1
        # small random jitter so we don't dog-pile
        await asyncio.sleep(random.uniform(0.3, 1.2))


async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    print(f"Load gen: {duration}s @ concurrency={concurrency}")
    print("Mix: ~85% success, ~10% 403, ~5% 401, occasional 429 if bob gets busy")

    stats: dict[str, int] = {}
    stop_at = time.time() + duration

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(worker(client, stop_at, stats) for _ in range(concurrency)))

    print("\n--- status code breakdown ---")
    for status in sorted(stats):
        print(f"  {status}: {stats[status]}")
    print(f"total: {sum(stats.values())}")


if __name__ == "__main__":
    asyncio.run(main())
