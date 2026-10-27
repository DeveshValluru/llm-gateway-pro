from openai import OpenAI


def make_client(api_key: str) -> OpenAI:
    return OpenAI(
        base_url="http://localhost:8000/v1",
        api_key=api_key,
    )


def try_request(label: str, client: OpenAI, model: str) -> None:
    print(f"\n--- {label} ---")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "What is wifi?"}],
            max_tokens=50,
        )
        print("OK:", resp.choices[0].message.content.strip())
    except Exception as e:
        print("ERR:", e)


if __name__ == "__main__":
    alice = make_client("sk-alice-dev-key")
    bob = make_client("sk-bob-dev-key")
    hacker = make_client("bad-key")

    # Alice has full access
    try_request("alice + pirate", alice, "pirate")
    try_request("alice + genz", alice, "genz")
    try_request("alice + formal", alice, "formal")

    # Bob can only use pirate
    try_request("bob + pirate (allowed)", bob, "pirate")
    try_request("bob + genz (forbidden)", bob, "genz")

    # Hacker has bad key
    try_request("hacker + pirate (bad key)", hacker, "pirate")
