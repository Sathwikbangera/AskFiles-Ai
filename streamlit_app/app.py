import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="RAG Doc Chat", page_icon="📄")
st.title("📄 RAG Doc Chat")
st.caption("Upload a document and ask questions — answers are grounded and cited.")

if "session_id" not in st.session_state:
    resp = requests.post(f"{BACKEND_URL}/session")
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
            resp = requests.post(f"{BACKEND_URL}/upload", files=files, data=data)

        if resp.ok:
            st.session_state.uploaded_files.append(uploaded.name)
            body = resp.json()
            st.success(f"Indexed {body['chunks_indexed']} chunks from {body['filename']}")
        else:
            st.error(resp.json().get("detail", "Upload failed"))

    if st.session_state.uploaded_files:
        st.write("**Indexed files:**")
        for name in st.session_state.uploaded_files:
            st.write(f"- {name}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input("Ask a question about your documents"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            resp = requests.post(
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
            error = resp.json().get("detail", "Something went wrong")
            st.error(error)
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {error}"})
