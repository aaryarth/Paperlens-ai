import uuid
import re
import hashlib
from datetime import datetime
from pathlib import Path


def generate_id() -> str:
    return str(uuid.uuid4())


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text


def file_hash(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def clean_text(text: str) -> str:
    """Remove excessive whitespace and control characters from extracted PDF text."""
    text = re.sub(r"\x00", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"-\n(\w)", r"\1", text)  # Rejoin hyphenated line breaks
    return text.strip()


def truncate(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def bytes_to_mb(b: int) -> float:
    return round(b / (1024 * 1024), 2)


def safe_filename(filename: str) -> str:
    return re.sub(r"[^\w\.\-]", "_", Path(filename).name)
