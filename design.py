import os
from typing import Optional, Union
import requests

from config import (
    STABILITY_API_KEY,
    STABILITY_API_HOST,
    STABILITY_OUTPUT_FORMAT,
    OUTPUT_DIR,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


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
        negative_prompt = "cartoon, low quality, bad architecture, warped lines, messy geometry, flat lighting"

    if not positive_prompt:
        raise ValueError("Prompt is empty.")

    # 🚀 تغییر استراتژیک به قدرتمندترین موتور استبیلیتی برای تغییر متریال و رنگ
    endpoint = f"{STABILITY_API_HOST}/v2beta/stable-image/generate/sd3"

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*",
    }

    data = {
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "mode": "image-to-image",  # 👈 دستور صریح برای پردازش تصویر روی تصویر
        "strength": "0.75",        # 👈 75 درصد تغییر (تضمین سبز شدن کابینت‌ها)
        "output_format": _normalize_output_format(STABILITY_OUTPUT_FORMAT),
        "model": "sd3"
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
            try:
                f.close()
            except Exception:
                pass

    if response.status_code != 200:
        raise RuntimeError(f"Stability API Error {response.status_code}: {response.text}")

    # ذخیره و بازگرداندن فایل نهایی
    output_format = data["output_format"]
    ext = "jpg" if output_format == "jpeg" else output_format
    output_path = os.path.join(OUTPUT_DIR, f"last_result.{ext}")
    
    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def _normalize_output_format(fmt: str) -> str:
    fmt = (fmt or "jpeg").strip().lower()
    if fmt in {"png", "jpeg", "webp"}:
        return fmt
    return "jpeg"
