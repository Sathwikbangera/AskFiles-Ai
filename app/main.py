from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="RAG Doc Chat",
    description="Upload documents, ask questions, get cited answers.",
)

app.include_router(router)
