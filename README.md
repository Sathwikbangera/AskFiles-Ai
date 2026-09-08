# AskFiles AI — RAG Doc Chat

Production-oriented document Q&A: upload files, ask questions, get answers
that are grounded in and cited from your documents — never the model's own
general knowledge.

**Live demo:** https://askfiles-ai.onrender.com/ (password-protected — ask for access)

**Screenshot:** _add a screenshot of the running app here (e.g. `docs/screenshot.png`)_

## Overview

This is a portfolio project built to demonstrate production RAG engineering
patterns, not just a LangChain quickstart wrapped in a UI. It upload-chunks
any PDF/DOCX/TXT, embeds and indexes it, and answers questions with forced
source citations. The interesting part isn't the demo itself — it's the
decisions underneath it: a provider-agnostic architecture that runs on free
tools locally and swaps to managed cloud services in production with zero
code changes, multi-tenant session isolation, and the cost/security hardening
a public-facing AI endpoint actually needs.

## Demo

Try it at **https://askfiles-ai.onrender.com/**:
1. Upload one or more PDF/DOCX/TXT files
2. Ask questions about them in the chat box
3. Every answer cites its source file and page
4. Ask something outside the uploaded documents — it refuses instead of guessing

Two notes on the live demo: it's gated behind a password (contact me for
access), and it's hosted on Render's free tier, which sleeps after ~15
minutes idle — the first request after a while can take 30-50 seconds to
wake up.

## Key Features

- **Multi-file, multi-document Q&A** — upload several files into one session and ask questions across all of them
- **Citation-grounded answers** — every claim cites `[source, page]`; refuses to answer from outside the retrieved context
- **Multi-tenant session isolation** — each upload session is tagged and filtered by `session_id` so documents never leak across users; sessions expire and their vectors are purged automatically
- **Swappable LLM providers** — Gemini, OpenAI, or Azure OpenAI, selected via one environment variable, no code changes
- **Swappable vector stores** — Chroma (local dev), Pinecone (production), or Azure AI Search, selected the same way
- **Prompt-injection screening** on user input
- **Public-endpoint hardening** — password gate and per-message length limits to protect free-tier API quotas from abuse
- **Automated grounding eval** — a fixed Q/A set (including an out-of-scope question) checked against the live API

## What This Project Demonstrates

| Skill | Where |
|---|---|
| RAG chatbot development | End-to-end: ingestion → retrieval → generation |
| Document Q&A systems | Multi-file upload and cross-document retrieval |
| OpenAI API integration | `app/services/llm_provider.py` (OpenAI + Azure OpenAI adapters) |
| Azure AI Search integration | `app/services/vectorstore_provider.py` `AzureSearchAdapter` |
| Vector / semantic search | Three interchangeable vector-store backends |
| Embedding pipelines | Page-aware chunking, metadata tagging, multi-provider embeddings |
| AI chatbot backend | FastAPI REST API (`/session`, `/upload`, `/chat`) |
| LLM evaluation / observability | `tests/run_eval.py` — automated grounding eval against the live API |
| LangChain integrations | Retrieval chain, text splitting, provider/vector-store abstractions |
| AI application security & governance | Prompt-injection guard, access gate, input limits, forced grounding |

## How It Works

1. A file is uploaded and split into pages, then chunked with overlap (`app/services/ingestion.py`)
2. Each chunk is embedded and stored tagged with the current `session_id`
3. A chat question triggers retrieval filtered to that `session_id` only
4. The top-k chunks are passed to the LLM with a system prompt that forces `[source, page]` citations and forbids answering outside the given context
5. Sessions (and their vectors) expire after `SESSION_TTL_HOURS` and are swept on the next request

## Architecture

```
Streamlit UI  --->  FastAPI backend  --->  LLM provider (swappable)
                          |                  Gemini (dev) / OpenAI / Azure OpenAI (demo)
                          v
                  Vector store (swappable)
                  Chroma (dev) / Pinecone (deployed) / Azure AI Search (demo adapter)
```

FastAPI and Streamlit run together in a single Docker container (`start.sh`)
on Render. The FastAPI backend is bound to `localhost` inside the container
and is never reachable from the public internet — only the Streamlit UI is
externally exposed, which talks to the backend server-side. This was
verified directly against the live deployment (backend routes return
Streamlit's own 404/405 responses when hit externally).

## Technical Highlights

Real issues hit and fixed while building this, since a resume claim is only
as good as what it survived:

- **Provider-agnostic adapter pattern**: a 3×3 matrix of LLM providers ×
  vector stores, selected entirely via `.env`, with no code branching in
  the application logic itself.
- **Caught a silent-corruption bug before it shipped**: assumed Gemini's
  embeddings were 768-dimensional (a common default); the actual output is
  3072-dimensional. Verified empirically before wiring Pinecone, since a
  wrong dimension would have made every future upsert fail.
- **Cross-store metadata normalization**: Pinecone and Azure AI Search
  coerce integer metadata to floats, silently turning `page 1` into
  `page 1.0` in citations. Normalized on read rather than assuming
  identical behavior across vector stores.
- **Handled upstream model deprecation**: two hardcoded Gemini model names
  (`text-embedding-004`, `gemini-2.0-flash`) were retired mid-build. Switched
  to Google's `-latest` alias pattern instead of pinning exact versions.
- **Diagnosed a misleading local SSL error**: a "certificate verify failed"
  error during local testing looked like corporate SSL inspection, but was
  actually a pre-existing local process (a print-management client)
  squatting on ports 8000/8443 and hijacking IPv6 "localhost" resolution.
  Root-caused via `netstat`/`wmic`, not by guessing.
- **Adapted to a platform policy change mid-build**: Hugging Face Spaces
  moved Docker-based Spaces behind a paid Pro plan after this project's
  deployment target was chosen. Re-scoped to Render with zero application
  code changes, since the same Docker container just needed a new host.
- **Hardened a public endpoint against cost abuse**: once deployed, added a
  shared-password gate and a per-message length cap specifically to protect
  free-tier LLM/vector-store quotas (which are easy to exhaust — Gemini's
  free tier allows only 20 chat requests/day per model).

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI |
| Orchestration | LangChain |
| LLM | Google Gemini / OpenAI / Azure OpenAI |
| Vector store | Chroma / Pinecone / Azure AI Search |
| Frontend | Streamlit |
| File parsing | pypdf, python-docx |
| Deployment | Docker, Render |
| Eval | Custom grounding eval against the live API |

## Provider Configuration

Set these in `.env` — no code changes required for any combination:

- `LLM_PROVIDER=gemini` (default, free) `| openai | azure_openai`
- `VECTOR_STORE=chroma` (default, local) `| pinecone | azure_search`

See `.env.example` for the full list of provider-specific keys.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# set GOOGLE_API_KEY, leave LLM_PROVIDER=gemini and VECTOR_STORE=chroma

uvicorn app.main:app --reload --port 8091
# in a second terminal:
streamlit run streamlit_app/app.py
```

> Port 8091 (not 8000) is deliberate: on Windows, other local software
> (e.g. print-management clients like uniFLOW SmartClient) commonly
> squats on 8000/8443, which can silently hijack "localhost" requests.
> `BACKEND_URL` in `.env` always uses `127.0.0.1` explicitly rather than
> `localhost` for the same reason — Windows can resolve `localhost` to
> the IPv6 loopback first, which such tools also occupy.

## Running the Evaluation

```bash
python tests/run_eval.py
```

Uploads `data/sample_docs/sample_policy.txt` and checks a fixed Q/A set
(including an out-of-scope question, to verify the model refuses to answer
from outside knowledge) for expected keywords against the live API.

## Deployment

Deployed as a single Docker container on **Render** (free tier), running
both the FastAPI backend and the Streamlit UI (`start.sh`), with
`LLM_PROVIDER=gemini` and `VECTOR_STORE=pinecone` in production. Streamlit
binds to Render's dynamically assigned `$PORT`.

(Originally targeted Hugging Face Spaces; moved to Render after Hugging
Face restricted free-tier Docker Spaces to paid Pro accounts — see
Technical Highlights.)

## Security

**In place:**
- Backend API has no public attack surface — only the Streamlit UI is
  externally reachable (verified against the live deployment)
- HTTPS enforced automatically by the hosting platform
- Secrets live only as environment variables, never committed to the repo
- Multi-tenant isolation via `session_id`-filtered vector queries
- Uploaded files are processed in memory only — never written to disk with
  a user-controlled filename (no path-traversal surface)
- Forced citation grounding reduces hallucination and makes answers auditable
- Password gate + per-message length cap on the public demo, to protect
  free-tier quotas from abuse
- Generic error responses to clients; no stack traces leak externally

**Known, honestly-disclosed gaps** (see Limitations below).

## Limitations

- The prompt-injection guard is a shallow regex heuristic on the user's
  typed question only — it does not screen uploaded document content, and
  is easy to bypass with rephrasing. Adequate for a demo, not for a
  production system handling untrusted multi-party documents.
- Session tracking is in-memory; a container restart silently orphans any
  vectors already written to Pinecone for sessions that existed at restart
  time (they're never TTL-cleaned since the tracker forgets them).
- No per-IP rate limiting beyond the password gate and message-length cap.
- Gemini's free tier caps out at 20 chat requests/day per model — real
  constraint on how much live demo traffic this can sustain without a paid
  key.
- No malware/content scanning on uploaded files.
- Render's free tier sleeps after ~15 minutes idle (cold start on next visit).

## Future Improvements

- Per-IP/session rate limiting
- Persistent (not in-memory) session store
- Stronger prompt-injection defense (LLM-based classifier instead of regex)
- Streaming chat responses
- Real RAGAS-based evaluation metrics (faithfulness, relevancy) instead of keyword checks
- CI pipeline running the eval suite on every push
- Azure OpenAI + Azure AI Search live demo clip (adapters are written and swappable, pending short Azure trial-credit use)

## License

MIT — see `LICENSE`.
