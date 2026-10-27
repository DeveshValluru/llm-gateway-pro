import streamlit as st
from openai import OpenAI

from config import PERSONALITIES, GATEWAY_URL

st.set_page_config(page_title="LLM Gateway", page_icon="🤖", layout="centered")
st.title("LLM Gateway — Personality Chat")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "API Key",
        value="sk-alice-dev-key",
        type="password",
        help="Try sk-alice-dev-key (all 3 personalities) or sk-bob-dev-key (pirate only).",
    )
    personality = st.selectbox("Personality", PERSONALITIES, index=0)
    max_tokens = st.slider("Max tokens", 50, 500, 150, 50)
    temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
    stream_mode = st.toggle("Stream responses", value=True)
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Say something…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    client = OpenAI(base_url=GATEWAY_URL, api_key=api_key)
    with st.chat_message("assistant"):
        try:
            if stream_mode:
                stream = client.chat.completions.create(
                    model=personality,
                    messages=st.session_state.messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )

                def token_gen():
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                reply = st.write_stream(token_gen())
            else:
                resp = client.chat.completions.create(
                    model=personality,
                    messages=st.session_state.messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                reply = resp.choices[0].message.content.strip()
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.error(f"Request failed: {e}")
