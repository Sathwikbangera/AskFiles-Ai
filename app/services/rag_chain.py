"""Retrieval + generation with forced source citation, so answers are grounded
in the uploaded documents rather than the model's own knowledge."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm_provider import get_chat_model
from app.services.vectorstore_provider import get_vectorstore

_SYSTEM_PROMPT = """You are a document Q&A assistant. Answer ONLY using the
provided context chunks below. Every claim must cite its source using the
format [source: <filename>, page <page>]. If the context does not contain
the answer, say you don't have enough information in the uploaded documents —
do not use outside knowledge."""


def _format_context(docs) -> str:
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        parts.append(f"[source: {source}, page {page}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def answer_question(session_id: str, question: str, k: int = 4) -> dict:
    retriever = get_vectorstore().as_retriever(session_id=session_id, k=k)
    docs = retriever.invoke(question)

    if not docs:
        return {
            "answer": "No documents found for this session yet — upload a file first.",
            "sources": [],
        }

    context = _format_context(docs)
    chat_model = get_chat_model()

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
    ]

    response = chat_model.invoke(messages)

    sources = [
        {"source": d.metadata.get("source"), "page": d.metadata.get("page")}
        for d in docs
    ]

    return {"answer": _extract_text(response.content), "sources": sources}


def _extract_text(content) -> str:
    """Some providers return content as a list of typed blocks instead of a
    plain string; normalize to plain text either way."""
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") for block in content if isinstance(block, dict)
    )
