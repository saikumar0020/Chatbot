import streamlit as st
import requests
import datetime

# Backend FastAPI endpoint
BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Agentic Chatbot",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("🤖 Agentic Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input at the bottom
if user_input := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                payload = {"question": user_input}
                response = requests.post(f"{BASE_URL}/query", json=payload)

                if response.status_code == 200:
                    answer = response.json().get("answer", "🤔 No response from agent.")
                else:
                    answer = f"❌ Error from agent: {response.status_code} - {response.text}"

            except Exception as e:
                answer = f"🚨 Request failed: {e}"

        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
