# 🔬 PaperLens AI

> Voice-enabled multi-document research assistant — upload PDFs, ask questions, compare papers, generate literature reviews, and identify research gaps using local or cloud LLMs.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal) ![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

| | |
|---|---|
| 📄 Multi-PDF upload | Drag-and-drop with FAISS indexing |
| 💬 Multi-paper Q&A | RAG-powered answers with citations |
| ⚖️ Cross-paper comparison | Methodology, datasets, results, conclusions |
| 📝 Summarization | Executive, detailed, findings, contributions |
| 🔍 Research gap analysis | Gaps, limitations, future work |
| 📖 Literature review | Auto-generated, grouped by theme |
| 🎙 Voice input | Faster-Whisper speech-to-text |
| 🔊 Voice output | Browser Speech Synthesis API |

---

## Architecture

```
Browser (HTML / JS / Voice UI)
          │
          ▼
     FastAPI backend
    ┌─────┴──────────────────────┐
    │                            │
Document layer              Voice layer
PyMuPDF + chunking       Faster-Whisper STT
    │
    ▼
Sentence Transformers
 all-MiniLM-L6-v2
    │
    ▼
 FAISS vector store
 (IndexFlatIP, cosine)
    │
    ▼
   LLM (RAG)
Ollama llama3 / OpenAI GPT-4o
```

---

## Quick start

```bash
git clone https://github.com/yourname/paperlens-ai.git
cd paperlens-ai

python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # defaults work for Ollama + llama3

ollama pull llama3

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** · API docs at **http://localhost:8000/docs**

---

## Docker

```bash
cp .env.example .env
docker-compose up -d --build
docker exec paperlens-ollama ollama pull llama3
```

---

## Using OpenAI instead of Ollama

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```



---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `TOP_K_RETRIEVAL` | `5` | Chunks retrieved per query |
| `FAISS_INDEX_PATH` | `./data/faiss_index` | FAISS persistence path |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size |

---

## Tech stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| LLM | Ollama (Llama 3) / OpenAI GPT-4o |
| Embeddings | Sentence Transformers |
| Vector DB | FAISS |
| PDF processing | PyMuPDF |
| Speech-to-text | Faster-Whisper |
| Text-to-speech | Web Speech Synthesis API |
| Validation | Pydantic v2 |
| Logging | Loguru |
| Containerization | Docker + Compose |

---

## License

MIT
