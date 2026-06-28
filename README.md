# 🔬 PaperLens AI

**Voice-Enabled Multi-Document Research Assistant**

PaperLens AI lets you upload multiple research papers (PDFs) and interact with them using text or voice. It answers questions, compares papers, generates summaries, identifies research gaps, and creates literature reviews — all powered by RAG (Retrieval-Augmented Generation).

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 Multi-PDF Upload | Drag-and-drop upload with validation and FAISS indexing |
| 💬 Multi-Paper Q&A | Ask questions across all papers with source citations |
| ⚖️ Cross-Paper Comparison | Compare methodology, datasets, results, conclusions |
| 📝 Paper Summarization | Executive, detailed, key findings, contributions, limitations |
| 🔍 Research Gap Analysis | Identify gaps, limitations, future work opportunities |
| 📖 Literature Review | Auto-generate review sections grouped by themes |
| 🎙 Voice Input | Faster-Whisper STT — speak your research questions |
| 🔊 Voice Output | Browser Speech Synthesis API reads answers aloud |
| 📊 Dashboard | Documents, chunks, embeddings, query & summary history |

---

## 🏗 Architecture

```
Browser (HTML/CSS/JS)
       │
       ▼
  FastAPI (Python)
       │
  ┌────┴──────────────┐
  │   Document Layer   │
  │  PyMuPDF + Chunks  │
  └────┬──────────────┘
       │
  ┌────┴──────────────┐
  │  Sentence Transformer│
  │  (all-MiniLM-L6-v2)  │
  └────┬──────────────┘
       │
  ┌────┴──────────────┐
  │   FAISS Vector DB  │
  └────┬──────────────┘
       │
  ┌────┴──────────────┐
  │   LangChain RAG    │
  │   Retriever + QA   │
  └────┬──────────────┘
       │
  ┌────┴──────────────┐
  │   Ollama (Llama3) │  ← default
  │   OpenAI GPT-4o   │  ← optional
  └───────────────────┘
```

---

## 🗂 Folder Structure

```
paperlens-ai/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── registry.py                # In-memory document registry
│   ├── routers/
│   │   ├── upload_router.py       # POST /upload, GET/DELETE /documents
│   │   ├── qa_router.py           # /ask /compare /summary /research-gaps /literature-review
│   │   ├── voice_router.py        # /voice/speech-to-text /voice/voice-query /voice/text-to-speech
│   │   └── dashboard_router.py    # GET /dashboard
│   ├── services/
│   │   ├── pdf_service.py         # PDF upload, validation, text extraction (PyMuPDF)
│   │   ├── chunk_service.py       # Semantic chunking with overlap
│   │   ├── embedding_service.py   # Sentence Transformers embeddings
│   │   ├── summary_service.py     # Multi-type paper summarization
│   │   ├── comparison_service.py  # Cross-paper comparison
│   │   ├── research_gap_service.py# Research gap analysis
│   │   ├── literature_review_service.py # Literature review generation
│   │   └── voice_service.py       # Faster-Whisper STT
│   ├── rag/
│   │   ├── retriever.py           # FAISS retrieval
│   │   ├── qa_chain.py            # LLM client (Ollama/OpenAI)
│   │   └── citation_handler.py    # Context builder + citation extractor
│   ├── vectorstore/
│   │   └── faiss_store.py         # FAISS vector store with persistence
│   ├── schemas/
│   │   └── __init__.py            # All Pydantic request/response models
│   ├── prompts/
│   │   └── __init__.py            # All LLM prompt templates
│   ├── config/
│   │   └── settings.py            # Pydantic-settings configuration
│   ├── utils/
│   │   ├── logger.py              # Loguru structured logging
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   └── helpers.py             # Utility functions
│   └── frontend/
│       ├── index.html             # Single-page application
│       ├── app.js                 # Full JS application
│       └── style.css              # Dark-themed UI
├── uploads/                       # PDF storage
├── audio/                         # Temp audio files
├── data/                          # FAISS index persistence
├── logs/                          # Application logs
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start (Local)

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) installed locally (for default LLM)
- ffmpeg (for voice: `brew install ffmpeg` / `apt install ffmpeg`)

### Step 1 — Clone & Setup

```bash
git clone https://github.com/yourname/paperlens-ai.git
cd paperlens-ai

python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Step 2 — Configure

```bash
cp .env.example .env
# Edit .env if needed (defaults work for Ollama + llama3)
```

### Step 3 — Pull Ollama Model

```bash
ollama pull llama3
```

### Step 4 — Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

API docs: **http://localhost:8000/docs**

---

## 🐳 Docker Deployment

```bash
# Copy and configure env
cp .env.example .env

# Build and start (Ollama + PaperLens)
docker-compose up -d --build

# Pull the LLM model inside Ollama container
docker exec paperlens-ollama ollama pull llama3

# Check logs
docker-compose logs -f paperlens
```

Open **http://localhost:8000**

---

## 🔧 Using OpenAI Instead of Ollama

Edit `.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```

---

## 📡 API Reference

### Upload Documents

```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf"
```

### List Documents

```bash
curl http://localhost:8000/upload/documents
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What deep learning architectures were compared?", "top_k": 5}'
```

### Compare Papers

```bash
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["<doc_id_1>", "<doc_id_2>"],
    "aspect": "methodology"
  }'
```

### Summarize Paper

```bash
curl -X POST http://localhost:8000/summary \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "<doc_id>",
    "summary_type": "executive"
  }'
```

### Research Gaps

```bash
curl -X POST http://localhost:8000/research-gaps \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Literature Review

```bash
curl -X POST http://localhost:8000/literature-review \
  -H "Content-Type: application/json" \
  -d '{"focus_topic": "transformer architectures"}'
```

### Voice Transcription

```bash
curl -X POST http://localhost:8000/voice/speech-to-text \
  -F "audio=@recording.wav"
```

### Voice Query (Full Pipeline)

```bash
curl -X POST http://localhost:8000/voice/voice-query \
  -F "audio=@question.webm"
```

### Dashboard

```bash
curl http://localhost:8000/dashboard
```

### Delete Document

```bash
curl -X DELETE http://localhost:8000/upload/documents/<doc_id>
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `OPENAI_API_KEY` | `` | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `FAISS_INDEX_PATH` | `./data/faiss_index` | FAISS persistence path |
| `UPLOAD_DIR` | `./uploads` | PDF storage directory |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size |
| `WHISPER_MODEL` | `base` | Faster-Whisper model (tiny/base/small/medium) |
| `TOP_K_RETRIEVAL` | `5` | Chunks retrieved per query |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## 🎙 Voice Usage

1. Click the **🎙 mic button** in the chat
2. Speak your research question clearly
3. Click the mic again to stop
4. The system transcribes (Faster-Whisper), retrieves, and answers
5. The answer is read aloud via browser Speech Synthesis

**Supported audio formats:** WAV, MP3, WebM, OGG, FLAC, M4A

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| LLM | Ollama (Llama 3) / OpenAI GPT-4o |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| Vector DB | FAISS |
| PDF Processing | PyMuPDF |
| Speech-to-Text | Faster-Whisper |
| Text-to-Speech | Web Speech Synthesis API |
| Validation | Pydantic v2 |
| Configuration | Pydantic-Settings |
| Logging | Loguru |
| Containerization | Docker + Docker Compose |

---

## 📄 License

MIT License — free to use, modify, and distribute.
