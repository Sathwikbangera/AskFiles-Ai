"""Swappable vector store: chroma (local dev) | pinecone (deployed) | azure_search (demo adapter).

All three are used as one shared index/collection with a `session_id` metadata
field for multi-tenant filtering, so uploaded documents from different chat
sessions never leak into each other's retrieval results.
"""

from app.config import settings
from app.services.llm_provider import get_embeddings

_EMBEDDING_DIMENSIONS = {
    "gemini": 3072,   # models/gemini-embedding-001 default output size
    "openai": 1536,   # text-embedding-3-small
    "azure_openai": 1536,  # assumes an equivalent small embedding deployment
}


class VectorStoreAdapter:
    def add_documents(self, docs: list, session_id: str) -> list[str]:
        raise NotImplementedError

    def as_retriever(self, session_id: str, k: int = 4):
        raise NotImplementedError

    def delete(self, ids: list[str]) -> None:
        raise NotImplementedError


class ChromaAdapter(VectorStoreAdapter):
    def __init__(self):
        from langchain_community.vectorstores import Chroma

        self.store = Chroma(
            collection_name="rag_doc_chat",
            embedding_function=get_embeddings(),
            persist_directory=settings.chroma_persist_dir,
        )

    def add_documents(self, docs, session_id: str) -> list[str]:
        for doc in docs:
            doc.metadata["session_id"] = session_id
        return self.store.add_documents(docs)

    def as_retriever(self, session_id: str, k: int = 4):
        return self.store.as_retriever(
            search_kwargs={"k": k, "filter": {"session_id": session_id}}
        )

    def delete(self, ids: list[str]) -> None:
        self.store.delete(ids=ids)


class PineconeAdapter(VectorStoreAdapter):
    def __init__(self):
        from pinecone import Pinecone, ServerlessSpec
        from langchain_pinecone import PineconeVectorStore

        client = Pinecone(api_key=settings.pinecone_api_key)
        dimension = _EMBEDDING_DIMENSIONS[settings.llm_provider]

        if settings.pinecone_index not in [i.name for i in client.list_indexes()]:
            client.create_index(
                name=settings.pinecone_index,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        self.store = PineconeVectorStore(
            index=client.Index(settings.pinecone_index),
            embedding=get_embeddings(),
        )

    def add_documents(self, docs, session_id: str) -> list[str]:
        for doc in docs:
            doc.metadata["session_id"] = session_id
        return self.store.add_documents(docs)

    def as_retriever(self, session_id: str, k: int = 4):
        return self.store.as_retriever(
            search_kwargs={"k": k, "filter": {"session_id": session_id}}
        )

    def delete(self, ids: list[str]) -> None:
        self.store.delete(ids=ids)


class AzureSearchAdapter(VectorStoreAdapter):
    def __init__(self):
        from langchain_community.vectorstores.azuresearch import AzureSearch

        self.store = AzureSearch(
            azure_search_endpoint=settings.azure_search_endpoint,
            azure_search_key=settings.azure_search_api_key,
            index_name=settings.azure_search_index,
            embedding_function=get_embeddings(),
        )

    def add_documents(self, docs, session_id: str) -> list[str]:
        for doc in docs:
            doc.metadata["session_id"] = session_id
        return self.store.add_documents(docs)

    def as_retriever(self, session_id: str, k: int = 4):
        return self.store.as_retriever(
            search_kwargs={"k": k, "filters": f"session_id eq '{session_id}'"}
        )

    def delete(self, ids: list[str]) -> None:
        self.store.delete(ids=ids)


_ADAPTERS = {
    "chroma": ChromaAdapter,
    "pinecone": PineconeAdapter,
    "azure_search": AzureSearchAdapter,
}

_adapter_instance = None


def get_vectorstore() -> VectorStoreAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        adapter_cls = _ADAPTERS.get(settings.vector_store)
        if adapter_cls is None:
            raise ValueError(f"Unknown VECTOR_STORE: {settings.vector_store}")
        _adapter_instance = adapter_cls()
    return _adapter_instance
