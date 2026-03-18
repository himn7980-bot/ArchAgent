import base64
from openai import OpenAI
from config import OPENAI_API_KEY, VISION_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def detect_scene(image_path: str) -> str:
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = """
Classify this architectural image.
Return only one word from:
interior
exterior
unfinished
renovation
"""

    result = client.responses.create(
        model=VISION_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{img_b64}",
                    },
                ],
            }
        ],
    )

    scene = result.output_text.strip().lower()
    return scene if scene in {"interior", "exterior", "unfinished", "renovation"} else "interior"