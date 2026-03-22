import base64
import os
from openai import OpenAI

from config import OPENAI_API_KEY, VISION_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def _image_to_data_url(image_path: str) -> str:
    if not image_path or not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return f"data:image/png;base64,{b64}"


def detect_scene(image_path: str) -> str:
    """
    Returns one of:
    - kitchen
    - bathroom
    - living_room
    - interior
    - exterior
    - unfinished
    """
    image_data_url = _image_to_data_url(image_path)

    system_prompt = """
You are an architectural scene classifier.

Classify the image into exactly one of these labels:
- kitchen
- bathroom
- living_room
- interior
- exterior
- unfinished

Rules:
- Ignore screenshot UI, overlays, social media controls, captions, icons, or watermarks.
- Focus only on the actual architectural scene.
- If it is an unfinished/raw concrete or under-construction building, return unfinished.
- If it is an outdoor building/facade/street view, return exterior.
- If it is clearly a kitchen, return kitchen.
- If it is clearly a bathroom, return bathroom.
- If it is clearly a living room / reception / sitting room, return living_room.
- Otherwise, if it is indoor, return interior.

Return only one label and nothing else.
""".strip()

    try:
        response = client.responses.create(
            model=VISION_MODEL,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Classify this architectural image.",
                        },
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                        },
                    ],
                },
            ],
        )

        text = (response.output_text or "").strip().lower()

        allowed = {"kitchen", "bathroom", "living_room", "interior", "exterior", "unfinished"}
        if text in allowed:
            return text

        if "kitchen" in text:
            return "kitchen"
        if "bathroom" in text:
            return "bathroom"
        if "living" in text:
            return "living_room"
        if "unfinished" in text or "construction" in text or "raw concrete" in text:
            return "unfinished"
        if "exterior" in text or "facade" in text or "building" in text:
            return "exterior"

        return "interior"

    except Exception:
        return "interior"
