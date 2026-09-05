"""In-memory registry of upload sessions so their vectors can be purged after
SESSION_TTL_HOURS. Swept lazily on each request rather than a background
scheduler, since this is a single-process portfolio deployment."""

import uuid
from datetime import datetime, timedelta

from app.config import settings
from app.services.vectorstore_provider import get_vectorstore

_sessions: dict[str, dict] = {}  # session_id -> {"created_at": dt, "doc_ids": [...]}


def create_session() -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"created_at": datetime.utcnow(), "doc_ids": []}
    return session_id


def register_docs(session_id: str, doc_ids: list[str]) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = {"created_at": datetime.utcnow(), "doc_ids": []}
    _sessions[session_id]["doc_ids"].extend(doc_ids)


def is_valid(session_id: str) -> bool:
    return session_id in _sessions


def sweep_expired() -> None:
    cutoff = datetime.utcnow() - timedelta(hours=settings.session_ttl_hours)
    expired = [sid for sid, s in _sessions.items() if s["created_at"] < cutoff]

    for sid in expired:
        doc_ids = _sessions[sid]["doc_ids"]
        if doc_ids:
            get_vectorstore().delete(doc_ids)
        del _sessions[sid]
