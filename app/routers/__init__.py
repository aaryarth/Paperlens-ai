from .upload_router import router as upload_router
from .qa_router import router as qa_router
from .voice_router import router as voice_router
from .dashboard_router import router as dashboard_router

__all__ = ["upload_router", "qa_router", "voice_router", "dashboard_router"]
