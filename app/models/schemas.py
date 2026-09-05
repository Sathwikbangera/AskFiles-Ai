from pydantic import BaseModel


class NewSessionResponse(BaseModel):
    session_id: str


class UploadResponse(BaseModel):
    session_id: str
    chunks_indexed: int
    filename: str


class ChatRequest(BaseModel):
    session_id: str
    question: str


class Source(BaseModel):
    source: str
    page: int | str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    flagged_input: bool = False
