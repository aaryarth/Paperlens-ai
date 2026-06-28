from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.voice_service import voice_service
from app.rag import retriever, llm_client, build_context, build_citations
from app.prompts import QA_PROMPT
from app.registry import registry
from app.schemas import (
    TranscriptionResponse,
    VoiceQueryResponse,
    TTSRequest,
    TTSResponse,
)
from app.utils import logger, to_http_exception
from app.utils.exceptions import PaperLensException

router = APIRouter(prefix="/voice", tags=["Voice"])

SUPPORTED_AUDIO = {
    ".wav", ".mp3", ".webm", ".ogg", ".flac", ".m4a", ".mp4"
}


def _validate_audio(filename: str | None) -> str:
    from pathlib import Path

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Missing audio filename."
        )

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_AUDIO:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {ext}. Supported: {', '.join(SUPPORTED_AUDIO)}"
        )

    return filename


@router.post("/speech-to-text", response_model=TranscriptionResponse, summary="Transcribe audio to text")
async def speech_to_text(audio: UploadFile = File(...)):
    filename = _validate_audio(audio.filename)
    try:
        content = await audio.read()
        result = voice_service.transcribe_audio(content, filename)
        return TranscriptionResponse(**result)
    except PaperLensException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-query", response_model=VoiceQueryResponse, summary="Ask a question via voice")
async def voice_query(audio: UploadFile = File(...)):

    filename = _validate_audio(audio.filename)

    if not registry.get_all_documents():
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded yet. Please upload PDFs before asking voice questions."
        )

    try:
        content = await audio.read()
        stt_result = voice_service.transcribe_audio(content, filename)
        transcript = stt_result["transcript"]

        if not transcript.strip():
            raise HTTPException(
                status_code=422,
                detail="Could not detect speech in the audio. Please speak clearly and try again."
            )

        logger.info(f"Voice query: '{transcript[:80]}'")

        chunks = retriever.retrieve(query=transcript, top_k=5)
        if not chunks:
            return VoiceQueryResponse(
                transcript=transcript,
                answer="I could not find relevant content in the uploaded documents to answer your question.",
                citations=[],
                model_used=llm_client.model_name,
            )

        context = build_context(chunks)
        prompt = QA_PROMPT.format(context=context, question=transcript)
        answer = llm_client.generate(prompt)
        citations = build_citations(chunks)

        registry.add_query(transcript, answer)

        return VoiceQueryResponse(
            transcript=transcript,
            answer=answer,
            citations=citations,
            model_used=llm_client.model_name,
        )
    except PaperLensException as e:
        raise to_http_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text-to-speech", response_model=TTSResponse, summary="Text-to-speech info endpoint")
async def text_to_speech(body: TTSRequest):
    return TTSResponse(
        message="Text ready for client-side speech synthesis.",
        text=body.text,
        note="Use the browser's SpeechSynthesis API to speak this text.",
    )
