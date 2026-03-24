import os
import random
from typing import Optional, Union
import requests

from config import (
    STABILITY_API_KEY,
    STABILITY_API_HOST,
    STABILITY_OUTPUT_FORMAT,
    STABILITY_SEED,
    OUTPUT_DIR,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_design(input_image_path: str, mask_path: Optional[str], prompt_data: Union[dict, str]) -> str:
    if not STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is missing.")

    if not os.path.exists(input_image_path):
        raise FileNotFoundError(f"Input image not found: {input_image_path}")

    if isinstance(prompt_data, dict):
        positive_prompt = prompt_data.get("prompt", "").strip()
        negative_prompt = prompt_data.get("negative_prompt", "").strip()
    else:
        positive_prompt = str(prompt_data).strip()
        negative_prompt = "cartoon, low quality, warped, messy, changing wall structure"

    # 🚀 این آدرس جادویی است: موتور تخصصی استراکچر معماری
    # دیگر به فایل config.py تو اعتماد نمی‌کنیم و مستقیماً به موتور درست وصل می‌شویم
    endpoint = f"{STABILITY_API_HOST}/v2beta/stable-image/control/structure"

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*",
    }

    current_seed = 0
    try: current_seed = int(STABILITY_SEED)
    except: pass
    if current_seed == 0:
        current_seed = random.randint(1000000, 9999999)

    # ارسال اطلاعات با پارامترهای اختصاصیِ موتور استراکچر
    data = {
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "output_format": "jpeg",
        "seed": str(current_seed),
        "control_strength": "0.7",  # 👈 ۷۰٪ وفاداری به جای دیوارها، ۱۰۰٪ آزادی برای تغییر رنگ و نور
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
