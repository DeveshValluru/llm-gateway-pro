from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="dev-secret-abc",
)
for model in ["pirate", "genz", "formal"]:
    resp = client.chat.completions.create(
        model = model,
        messages = [{
            "role":"user", "content":
            "what is gravity?"
        }],
        max_tokens = 150,
        temperature = 0.7,
    )

    print(f"\n=== {model.upper()} ===")
    print(resp.choices[0].message.content)
