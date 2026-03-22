import os
from openai import OpenAI

from config import OPENAI_API_KEY, TRANSCRIBE_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def _normalize_lang(lang: str) -> str:
    if not lang:
        return "en"

    lang = lang.strip().lower()

    if lang.startswith("fa") or lang in {"persian", "farsi"}:
        return "fa"
    if lang.startswith("ar") or lang == "arabic":
        return "ar"
    if lang.startswith("ru") or lang == "russian":
        return "ru"
    if lang.startswith("en") or lang == "english":
        return "en"

    return "en"


def transcribe_voice(voice_path: str) -> dict:
    """
    Returns:
    {
        "text": "...",
        "language": "fa" | "ar" | "en" | "ru"
    }
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing.")

    if not voice_path or not os.path.exists(voice_path):
        raise FileNotFoundError(f"Voice file not found: {voice_path}")

    with open(voice_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=audio_file,
            response_format="verbose_json",
        )

    text = (getattr(result, "text", None) or "").strip()
    detected_language = _normalize_lang(getattr(result, "language", None) or "")

    return {
        "text": text,
        "language": detected_language,
    }
