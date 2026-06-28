import os
import tempfile
from pathlib import Path
from typing import Dict, Any

from app.config import settings
from app.utils import logger, AudioProcessingError


class VoiceService:
    """
    Handles audio transcription using Faster-Whisper.
    Text-to-Speech is handled client-side via the Web Speech Synthesis API.
    """

    def __init__(self):
        self.audio_dir = Path(settings.audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._model = None

    def _get_model(self):
        """Lazy-load Faster-Whisper model."""
        if self._model is None:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Faster-Whisper model: {settings.whisper_model}")
            self._model = WhisperModel(
                settings.whisper_model,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Faster-Whisper model loaded.")
        return self._model

    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Transcribe audio bytes to text using Faster-Whisper.

        Args:
            audio_bytes: raw audio file content (wav, mp3, webm, ogg, etc.)
            filename: original filename (used to determine extension)

        Returns:
            Dict with keys: transcript, language, confidence, duration_seconds
        """
        # Save to temp file
        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            dir=str(self.audio_dir),
            delete=False
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            model = self._get_model()
            logger.info(f"Transcribing: {tmp_path} ({len(audio_bytes)} bytes)")

            segments, info = model.transcribe(
                tmp_path,
                beam_size=5,
                language=None,  # auto-detect
                vad_filter=True,
            )

            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text.strip())

            transcript = " ".join(transcript_parts).strip()
            duration = info.duration if hasattr(info, "duration") else None
            language = info.language if hasattr(info, "language") else "unknown"
            confidence = (
                info.language_probability if hasattr(info, "language_probability") else None
            )

            message = f"Transcription complete. Language: {language}, "
            if duration is not None:
                message += f"Duration: {duration:.1f}s, "
            message += f"Text length: {len(transcript)}"
            logger.info(message)

            return {
                "transcript": transcript,
                "language": language,
                "confidence": round(confidence, 3) if confidence else None,
                "duration_seconds": round(duration, 2) if duration else None,
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise AudioProcessingError(str(e))
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


voice_service = VoiceService()
