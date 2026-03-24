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

Rules: Return only one label and nothing else.
""".strip()

    try:
        # سینتکس درست و استاندارد OpenAI برای پردازش تصویر
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt + "\n\nClassify this architectural image."},
                        {"type": "image_url", "image_url": {"url": image_data_url}}
                    ]
                }
            ],
            max_tokens=10
        )

        # استخراج درست متن از جواب OpenAI
        text = response.choices[0].message.content.strip().lower()
        print(f"AI Detected Scene: {text}") # چاپ در لاگ سرور برای دیباگ

        allowed = {"kitchen", "bathroom", "living_room", "interior", "exterior", "unfinished"}
        
        for kw in allowed:
            if kw in text:
                return kw

        return "interior"

    except Exception as e:
        print(f"Vision API Error: {e}")
        return "interior"


def translate_request_to_english(user_text: str) -> str:
    """
    Turn user's raw request into a short, clear English architectural edit request
    for image generation.
    """
    if not user_text or not user_text.strip():
        return ""

    system_prompt = """
You convert architectural edit requests into clear English prompts for image generation.
Rules:
- Return ONLY English.
- Keep color, style, material, lighting, weather, and time-of-day instructions.
- Make it concise and image-generation friendly.
- Do not explain anything. Just output the translated prompt.
""".strip()

    try:
        # سینتکس درست و استاندارد OpenAI برای متن
        response = client.chat.completions.create(
            model="gpt-4o-mini", # استفاده از مدل سریع و ارزان برای ترجمه
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text.strip()}
            ],
            max_tokens=100
        )
        
        # استخراج درست متن از جواب
        english_text = response.choices[0].message.content.strip()
        print(f"Original: {user_text} | Translated: {english_text}") # چاپ در لاگ
        return english_text
        
    except Exception as e:
        print(f"Translation API Error: {e}")
        return "Make it look professional and redesigned" # به جای برگرداندن متن فارسی، یک پرامپت جنرال بفرست تا حداقل کار کند
