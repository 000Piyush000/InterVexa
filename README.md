# AI Interview Copilot (RAG)

A fully local, Retrieval-Augmented Generation web application that helps candidates prepare for
technical interviews using **real interview experiences** they upload (PDF/TXT). Every answer is
retrieved from the uploaded documents and generated with a locally-hosted Llama 3 model via
[Ollama](https://ollama.com) — no paid APIs, no data leaving your machine.

---

## Overview

Upload company-specific interview experience documents (e.g. `Amazon_Interview_2024.pdf`), and the
app will automatically extract the text, clean it, split it into chunks, embed those chunks with
Sentence Transformers, and store the vectors in a persistent FAISS index. You can then chat with the
copilot — filtered by company and by interview mode (DSA, System Design, SQL, HR) — and every answer
comes with citations pointing back to the exact document and chunk it was drawn from.

If the uploaded documents don't contain the answer, the copilot says so explicitly instead of making
something up.

## Features

- **Modern landing page** with hero section, company cards, and dark mode.
- **Upload system** for PDF/TXT files, organized by company (Amazon, Google, Microsoft, Adobe, Meta,
  or any custom company you type in).
- **Automatic processing pipeline** — text extraction → cleaning → chunking → embedding → FAISS
  indexing — runs the moment you upload, with no manual steps.
- **RAG-powered chat** — semantic search retrieves the top-5 most relevant chunks, which are injected
  into a strict prompt template and sent to a local Llama 3 model.
- **Source citations** on every answer (document name + chunk number).
- **Interview modes** — DSA, System Design, SQL, and HR — that re-rank retrieval and steer the prompt
  toward the round you're prepping for.
- **Grounded answers only** — the model is instructed to say *"The uploaded documents do not contain
  this information."* whenever the context doesn't support an answer.
- **Polished Bootstrap 5 UI** — chat bubbles, typing animation, auto-scroll, suggested questions,
  loading spinners, toast notifications, empty-state illustrations, full mobile support.
- **Bonus features** — persistent chat history, download conversation as PDF, search within the
  current conversation, favorite questions, frequently-asked-topics panel, a confidence indicator per
  answer, and dark mode that persists across visits.

## Architecture

```
                    ┌────────────────────┐
                    │   Browser (UI)     │
                    │  Bootstrap 5 + JS  │
                    └─────────┬──────────┘
                              │ HTTP / fetch
                    ┌─────────▼──────────┐
                    │      app.py        │
                    │  Flask route layer │
                    └───┬────────────┬───┘
                        │            │
          ┌─────────────▼───┐   ┌────▼─────────────┐
          │  Upload/Process  │   │   Chat / Ask      │
          │  pipeline        │   │   pipeline        │
          └───────┬──────────┘   └────────┬──────────┘
                  │                       │
     ┌────────────▼────────────┐         │
     │ utils/pdf_loader.py     │         │
     │ utils/chunker.py        │         │
     │ utils/embeddings.py     │         │
     │ utils/vector_store.py   │◄────────┤ retrieval
     └────────────┬────────────┘         │
                  │                      │
        ┌─────────▼─────────┐  ┌─────────▼─────────┐
        │  FAISS index       │  │ utils/retriever.py │
        │  (embeddings/)      │  │ utils/prompt.py    │
        └─────────────────────┘  │ utils/llm.py       │
                                  └─────────┬──────────┘
                                            │
                                  ┌─────────▼──────────┐
                                  │   Ollama (Llama 3)  │
                                  │   local inference    │
                                  └──────────────────────┘
```

### RAG pipeline

```
PDF/TXT Upload
     │
Text Extraction (pypdf)
     │
Text Cleaning
     │
Chunking (LangChain RecursiveCharacterTextSplitter)
     │
Sentence-Transformer Embeddings (all-MiniLM-L6-v2)
     │
FAISS Vector Store (persisted to embeddings/<company>/)
     │
     ▼
User Question ──► Similarity Search ──► Top-5 Chunks ──► Prompt Construction ──► Llama 3 (Ollama) ──► Answer + Citations
```

## Folder structure

```
Interview-Copilot-RAG/
│
├── app.py                  # Flask route layer (thin — logic lives in utils/)
├── config.py                # Central configuration (paths, models, modes, constants)
├── requirements.txt
├── README.md
├── .gitignore
│
├── templates/
│   ├── index.html            # Landing page
│   ├── upload.html           # Upload UI
│   └── chat.html             # Chat UI
│
├── static/
│   ├── css/style.css         # Custom styles layered on Bootstrap 5
│   ├── js/chat.js             # All front-end logic (theme, upload, chat)
│   └── uploads/                # (unused placeholder — uploads are saved under data/)
│
├── data/                     # Uploaded source documents, organized by company
│   ├── Amazon/
│   ├── Google/
│   ├── Microsoft/
│   ├── Adobe/
│   └── Meta/
│
├── embeddings/                # Persistent per-company FAISS indexes + manifests
│
└── utils/
    ├── pdf_loader.py          # PDF/TXT extraction + text cleaning
    ├── chunker.py               # Text splitting into cited chunks
    ├── embeddings.py           # Sentence-Transformer embeddings (LangChain-compatible)
    ├── vector_store.py         # Persistent FAISS index management per company
    ├── retriever.py             # Semantic search + mode re-ranking + confidence scoring
    ├── llm.py                    # Ollama client wrapper (Llama 3)
    ├── prompt.py                 # Strict, anti-hallucination prompt templates
    ├── file_utils.py             # Upload validation & safe file saving
    ├── topics.py                  # Frequently-asked-topics analysis (bonus)
    └── chat_export.py             # PDF chat transcript export (bonus)
```

## Installation

### 1. Prerequisites

- Python 3.11
- [Ollama](https://ollama.com/download) installed locally

### 2. Clone / open the project

```bash
cd Interview-Copilot-RAG
```

### 3. Create a virtual environment and install dependencies

```bash
python3.11 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The first run will download the `all-MiniLM-L6-v2` Sentence-Transformer model (~90 MB) from
HuggingFace and cache it locally — this requires internet access once, after which everything runs
offline.

### 4. Set up Ollama + Llama 3

```bash
# Install Ollama from https://ollama.com/download, then:
ollama serve            # start the local Ollama server (if not already running)
ollama pull llama3      # download the Llama 3 model (a few GB, one-time download)
```

Verify it's working:

```bash
ollama run llama3 "Say hello"
```

### 5. Run the application

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

> The app also runs fine without Ollama running — you'll be able to upload and process documents, but
> the chat page will show a warning banner and any question you ask will return a clear error message
> until Ollama is started.

## Using the app

1. Go to **Upload**, pick a company (or type a custom one), and drag in a few PDF/TXT interview
   experience files. They're processed automatically.
2. Go to **Chat**, pick the same company and an interview mode (General / DSA / System Design / SQL /
   HR), and start asking questions such as:
   - "What DSA questions were asked at Amazon?"
   - "What HR questions are common at Google?"
   - "Give me SQL questions asked by Microsoft."
   - "Summarize interview experiences for Adobe."
   - "What topics appear most frequently?"
3. Every answer shows a **confidence indicator** and a **Sources** list of the document + chunk it
   used. If nothing relevant was found, the copilot tells you directly instead of guessing.
4. Use the sidebar to browse **suggested questions** and **frequently asked topics**, star a question
   to save it under **Favorites**, search within the current conversation, export it as a PDF, or
   clear it entirely.

## Configuration

All tunables live in `config.py`, including:

- `CHUNK_SIZE` / `CHUNK_OVERLAP` — chunking granularity
- `TOP_K` — how many chunks are retrieved per question
- `MIN_RELEVANCE_SCORE` — similarity threshold below which a chunk is treated as irrelevant
- `OLLAMA_MODEL` / `OLLAMA_HOST` — override via environment variables `OLLAMA_MODEL` / `OLLAMA_HOST`
- `EMBEDDING_MODEL_NAME` — defaults to `all-MiniLM-L6-v2`

## Performance notes

- FAISS indexes are **persisted to disk** per company under `embeddings/<company>/` and reloaded on
  demand — they are not rebuilt on every request.
- A `manifest.json` per company tracks which source files (by name, size and modification time) have
  already been embedded, so re-running the pipeline only processes new or changed files.
- The Sentence-Transformer model and each company's FAISS index are cached in memory after first use
  within the running process.

## Error handling

The app fails gracefully and shows friendly messages for:

- Invalid, corrupted, or password-protected PDFs
- Empty or unsupported file uploads (only `.pdf` / `.txt` are accepted)
- Oversized uploads (configurable `MAX_CONTENT_LENGTH_MB`, default 20MB per file)
- A missing/unreachable Ollama server (`OllamaUnavailableError`)
- A model that hasn't been pulled yet in Ollama (`OllamaModelMissingError`)
- Asking a question before any documents have been processed for that company

## Screenshots

_Add screenshots of the landing page, upload flow, and chat interface here once you've run the app
locally, e.g.:_

```
docs/screenshot-landing.png
docs/screenshot-upload.png
docs/screenshot-chat.png
```

## Future improvements

- Streaming token-by-token responses from Ollama for a faster perceived response time
- Multi-company comparison queries ("compare DSA difficulty between Amazon and Google")
- Re-ranking retrieved chunks with a cross-encoder for higher precision
- User accounts with per-user chat history stored in a real database instead of the Flask session
- OCR support for scanned/image-only PDFs
- Automated evaluation harness to measure groundedness and citation accuracy over time

## Tech stack

Python 3.11 &middot; Flask &middot; LangChain &middot; FAISS &middot; Sentence Transformers
(`all-MiniLM-L6-v2`) &middot; Ollama + Llama 3 &middot; PyPDF &middot; Bootstrap 5 &middot;
vanilla HTML/CSS/JavaScript. No paid APIs are used anywhere in this project.
