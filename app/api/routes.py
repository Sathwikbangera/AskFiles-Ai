from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.guardrails.prompt_injection import guard_user_input
from app.models.schemas import ChatRequest, ChatResponse, NewSessionResponse, UploadResponse
from app.services.ingestion import SUPPORTED_EXTENSIONS, chunk_file
from app.services.rag_chain import answer_question
from app.services.session_manager import create_session, is_valid, register_docs, sweep_expired
from app.services.vectorstore_provider import get_vectorstore

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/session", response_model=NewSessionResponse)
def new_session():
    sweep_expired()
    return NewSessionResponse(session_id=create_session())


@router.post("/upload", response_model=UploadResponse)
async def upload(session_id: str = Form(...), file: UploadFile = File(...)):
    sweep_expired()

    if not is_valid(session_id):
        raise HTTPException(status_code=404, detail="Unknown or expired session_id")

    ext = "." + file.filename.lower().rsplit(".", 1)[-1]
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit"
        )

    docs = chunk_file(file.filename, content)
    if not docs:
        raise HTTPException(status_code=400, detail="No extractable text found in file")

    doc_ids = get_vectorstore().add_documents(docs, session_id=session_id)
    register_docs(session_id, doc_ids)

    return UploadResponse(
        session_id=session_id, chunks_indexed=len(docs), filename=file.filename
    )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    sweep_expired()

    if not is_valid(request.session_id):
        raise HTTPException(status_code=404, detail="Unknown or expired session_id")

    question, flagged = guard_user_input(request.question)
    result = answer_question(session_id=request.session_id, question=question)

    return ChatResponse(
        answer=result["answer"], sources=result["sources"], flagged_input=flagged
    )
