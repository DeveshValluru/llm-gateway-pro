import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

QUESTIONS = [
    "What is gravity?",
    "How does wifi work?",
    "Why is the sky blue?",
    "What is a black hole?",
    "How do airplanes fly?",
    "What causes rain?",
    "Why do we sleep?",
    "What is electricity?",
    "How does the internet work?",
    "What is a virus?",
    "Why is the ocean salty?",
    "How do computers work?",
    "What is DNA?",
    "How does a car engine work?",
    "What causes earthquakes?",
    "Why do leaves change color?",
    "What is photosynthesis?",
    "How do magnets work?",
    "What is the speed of light?",
    "Why do we dream?",
    "How do I make pasta?",
    "How do I tie a tie?",
    "How do I change a tire?",
    "How do I bake a cake?",
    "How do I fold a paper airplane?",
    "How do I make coffee?",
    "How do I plant a tree?",
    "How do I learn a new language?",
    "How do I save money?",
    "How do I meditate?",
    "What is machine learning?",
    "What is a database?",
    "What is an algorithm?",
    "What is cloud computing?",
    "What is a firewall?",
    "What is blockchain?",
    "What is quantum computing?",
    "What is a compiler?",
    "What is recursion?",
    "What is an API?",
    "What is the best pizza topping?",
    "Is cereal a soup?",
    "What is the meaning of life?",
    "Is a hotdog a sandwich?",
    "What is the best programming language?",
    "Should I get a dog or a cat?",
    "What is the best movie ever?",
    "Coffee or tea?",
    "Beach or mountains?",
    "What makes a good friend?",
]

PERSONALITIES = {
    "pirate": (
        "You are a pirate from the golden age of piracy. Respond to every question "
        "in pirate speak. Use words like 'arrr', 'matey', 'ye', 'aye', 'ahoy', "
        "'landlubber', 'scallywag'. Reference the sea, ships, treasure, and rum. "
        "Keep answers to 2-3 sentences. Always stay in character."
    ),
    "genz": (
        "You are a Gen Z teenager responding to questions. Use Gen Z slang like "
        "'no cap', 'fr fr', 'lowkey', 'highkey', 'bruh', 'bet', 'slay', 'vibe', "
        "'it's giving', 'periodt', 'bussin'. Be casual and use lowercase mostly. "
        "Keep answers to 2-3 sentences. Always stay in character."
    ),
    "formal": (
        "You are a highly polished corporate executive responding to questions. "
        "Use sophisticated vocabulary, formal grammar, and professional tone. "
        "Employ phrases like 'I would posit', 'one might consider', 'it is my "
        "considered opinion', 'permit me to elucidate'. Keep answers to 2-3 "
        "sentences. Always stay in character."
    ),
}


os.makedirs("data", exist_ok=True)

for name,system_prompt in PERSONALITIES.items():
    with open(f"data/{name}.jsonl", "w") as f:
        print(f"generating {name} data.....")

        for question in QUESTIONS:
            answer = client.messages.create(
                model = "claude-haiku-4-5",
                max_tokens = 200,
                system = system_prompt,
                messages = [{"role": "user", "content":question}]
            )
            answer_text = answer.content[0].text

            record = {"messages":[
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer_text}
            ]}

            f.write(json.dumps(record)+ "\n")

print("done with the data generation!!")



