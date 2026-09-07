import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)  # override so a stray shell env var can't shadow .env

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8091")
MAX_QUESTION_CHARS = 2000

http = requests.Session()
http.trust_env = False


def error_detail(resp) -> str:
    """FastAPI's `detail` is a plain string for HTTPException but a list of
    error objects for pydantic validation errors (e.g. question too long)."""
    detail = resp.json().get("detail", "Something went wrong")
    if isinstance(detail, list):
        return "; ".join(d.get("msg", str(d)) for d in detail)
    return detail


APP_PASSWORD = os.getenv("APP_PASSWORD", "")

st.set_page_config(page_title="RAG Doc Chat", page_icon="📄")

if APP_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("📄 RAG Doc Chat")
        pwd = st.text_input("Enter access password", type="password")
        if pwd:
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        st.stop()

st.title("📄 RAG Doc Chat")
st.caption("Upload a document and ask questions — answers are grounded and cited.")

if "session_id" not in st.session_state:
    resp = http.post(f"{BACKEND_URL}/session")
    resp.raise_for_status()
    st.session_state.session_id = resp.json()["session_id"]
    st.session_state.messages = []
    st.session_state.uploaded_files = []

with st.sidebar:
    st.subheader("Upload documents")
    uploaded = st.file_uploader("PDF, DOCX, or TXT", type=["pdf", "docx", "txt", "md"])

    if uploaded and uploaded.name not in st.session_state.uploaded_files:
        with st.spinner(f"Indexing {uploaded.name}..."):
            files = {"file": (uploaded.name, uploaded.getvalue())}
            data = {"session_id": st.session_state.session_id}
            resp = http.post(f"{BACKEND_URL}/upload", files=files, data=data)

        if resp.ok:
            st.session_state.uploaded_files.append(uploaded.name)
            body = resp.json()
            st.success(f"Indexed {body['chunks_indexed']} chunks from {body['filename']}")
        else:
            st.error(error_detail(resp))

    if st.session_state.uploaded_files:
        st.write("**Indexed files:**")
        for name in st.session_state.uploaded_files:
            st.write(f"- {name}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input(
    "Ask a question about your documents", max_chars=MAX_QUESTION_CHARS
):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            resp = http.post(
                f"{BACKEND_URL}/chat",
                json={"session_id": st.session_state.session_id, "question": question},
            )

        if resp.ok:
            body = resp.json()
            answer = body["answer"]
            if body.get("flagged_input"):
                st.warning("Your input looked like a prompt-injection attempt — treated as plain text.")
            st.markdown(answer)
            if body["sources"]:
                with st.expander("Sources"):
                    for s in body["sources"]:
                        st.write(f"- {s['source']} (page {s['page']})")
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            error = error_detail(resp)
            st.error(error)
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {error}"})
