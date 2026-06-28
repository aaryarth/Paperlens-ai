import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.utils import logger
from app.utils.exceptions import PaperLensException
from app.routers import upload_router, qa_router, voice_router, dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  PaperLens AI – Voice-Enabled Research Assistant")
    logger.info("=" * 60)
    logger.info(f"  LLM Provider : {settings.llm_provider}")
    logger.info(f"  LLM Model    : {settings.ollama_model if settings.llm_provider == 'ollama' else settings.openai_model}")
    logger.info(f"  Embeddings   : {settings.embedding_model}")
    logger.info(f"  Whisper      : {settings.whisper_model}")
    logger.info(f"  Upload Dir   : {settings.upload_dir}")
    logger.info(f"  FAISS Path   : {settings.faiss_index_path}")
    logger.info("=" * 60)
    yield
    logger.info("PaperLens AI shutting down.")


app = FastAPI(
    title="PaperLens AI",
    description=(
        "Voice-Enabled Multi-Document Research Assistant. "
        "Upload research papers and interact via text or voice to get answers, "
        "summaries, comparisons, research gap analyses, and literature reviews."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(PaperLensException)
async def paperlens_exception_handler(request: Request, exc: PaperLensException):
    logger.error(f"PaperLensException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc), "status_code": 500},
    )

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(upload_router)
app.include_router(qa_router)
app.include_router(voice_router)
app.include_router(dashboard_router)

# ─── Static Frontend ──────────────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
    }
