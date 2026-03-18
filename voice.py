from openai import OpenAI
from config import OPENAI_API_KEY, TRANSCRIBE_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe_voice(audio_path: str) -> str:
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=audio_file,
        )
    return transcript.text.strip()