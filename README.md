# RAG Doc Chat

Upload a document (PDF/DOCX/TXT), ask questions about it, get answers grounded
in and cited from the document — not the model's general knowledge.

## Architecture

```
Streamlit UI  --->  FastAPI backend  --->  LLM provider (swappable)
                          |                  Gemini (dev) / OpenAI / Azure OpenAI (demo)
                          v
                  Vector store (swappable)
                  Chroma (dev) / Pinecone (deployed) / Azure AI Search (demo adapter)
```

Every uploaded file is chunked, embedded, and stored tagged with a
`session_id`. Chat queries are filtered to that session so different users'
documents never mix. Sessions expire after `SESSION_TTL_HOURS` and their
vectors are purged.

The LLM and vector store are both selected at runtime via environment
variables (`LLM_PROVIDER`, `VECTOR_STORE`) behind a common interface
(`app/services/llm_provider.py`, `app/services/vectorstore_provider.py`),
so the same code runs against free local tools during development and
against managed cloud services in production.

## Local development (free: Gemini + Chroma)

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# set GOOGLE_API_KEY, leave LLM_PROVIDER=gemini and VECTOR_STORE=chroma

uvicorn app.main:app --reload --port 8000
# in a second terminal:
streamlit run streamlit_app/app.py
```

## Running the grounding eval

```bash
python tests/run_eval.py
```

Uploads `data/sample_docs/sample_policy.txt` and checks a fixed Q/A set
(including an out-of-scope question, to verify the model refuses to answer
from outside knowledge) for expected keywords.

## Swapping providers

- `LLM_PROVIDER=openai` — real OpenAI API (needs `OPENAI_API_KEY`)
- `LLM_PROVIDER=azure_openai` — Azure OpenAI (needs Azure OpenAI env vars)
- `VECTOR_STORE=pinecone` — Pinecone serverless (needs `PINECONE_API_KEY`)
- `VECTOR_STORE=azure_search` — Azure AI Search free F0 tier (needs Azure Search env vars)

No code changes required — just `.env` values.

## Deployment

Deployed as a single Docker container on Hugging Face Spaces (free tier),
running both the FastAPI backend and the Streamlit UI (`start.sh`).
Production config: `LLM_PROVIDER=gemini`, `VECTOR_STORE=pinecone`.

## Security notes

- Uploads are limited to `MAX_UPLOAD_MB` and restricted file types.
- User input is screened for common prompt-injection patterns
  (`app/guardrails/prompt_injection.py`); flagged input is still answered
  but surfaced to the user as a warning.
- Answers are instructed to cite `[source, page]` for every claim and to
  refuse to answer from outside the retrieved context.
