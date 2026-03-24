import os
import random
from typing import Optional, Union
import requests

from config import (
    STABILITY_API_KEY,
    STABILITY_API_HOST,
    STABILITY_IMAGE_MODEL,
    STABILITY_OUTPUT_FORMAT,
    STABILITY_SEED,
    OUTPUT_DIR,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def _build_endpoint() -> str:
    # 👈 مشکل دقیقاً اینجا بود که اصلاح شد (IMAGE به جای API)
    model_path = STABILITY_IMAGE_MODEL.strip().lstrip("/")
    return f"{STABILITY_API_HOST}/v2beta/{model_path}"


def generate_design(input_image_path: str, mask_path: Optional[str], prompt_data: Union[dict, str]) -> str:
    if not STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is missing.")

    if not os.path.exists(input_image_path):
        raise FileNotFoundError(f"Input image not found: {input_image_path}")

    # استخراج پرامپت‌ها
    if isinstance(prompt_data, dict):
        positive_prompt = prompt_data.get("prompt", "").strip()
        negative_prompt = prompt_data.get("negative_prompt", "").strip()
    else:
        positive_prompt = str(prompt_data).strip()
        negative_prompt = "cartoon, low quality, warped, messy, changing wall structure"

    if not positive_prompt:
        raise ValueError("Prompt is empty.")

    endpoint = _build_endpoint()
    output_format = _normalize_output_format(STABILITY_OUTPUT_FORMAT)

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*",
    }

    # عدد جادویی برای حفظ هندسه آشپزخانه: 0.65
    optimal_strength = 0.65

    # تولید عدد رندوم واقعی
    current_seed = _normalize_seed(STABILITY_SEED)
    if current_seed == 0:
        current_seed = random.randint(1000000, 9999999)

    data = {
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "output_format": output_format,
        "seed": str(current_seed),
        "strength": str(optimal_strength), 
        "control_strength": str(optimal_strength),
        "cfg_scale": "9.0"
    }

    files = {
        "image": open(input_image_path, "rb"),
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            files=files,
            data=data,
            timeout=180,
        )
    finally:
        for f in files.values():
            try: f.close()
            except Exception: pass

    if response.status_code != 200:
        raise RuntimeError(f"Stability API Error {response.status_code}: {response.text}")

    output_path = os.path.join(OUTPUT_DIR, f"last_result.jpg")
    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def _normalize_output_format(fmt: str) -> str:
    fmt = (fmt or "jpeg").strip().lower()
    return fmt if fmt in {"png", "jpeg", "webp"} else "jpeg"

def _normalize_seed(seed: int) -> int:
    try: return max(0, int(seed))
    except: return 0
