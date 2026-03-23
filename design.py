import os
from typing import Optional, Union

import requests

from config import (
    STABILITY_API_KEY,
    STABILITY_API_HOST,
    STABILITY_IMAGE_MODEL,
    STABILITY_OUTPUT_FORMAT,
    STABILITY_SEED,
    STABILITY_CFG_SCALE,
    STABILITY_STRENGTH,
    OUTPUT_DIR,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def _build_endpoint() -> str:
    model_path = STABILITY_IMAGE_MODEL.strip().lstrip("/")
    return f"{STABILITY_API_HOST}/v2beta/{model_path}"


def _validate_file(path: str, label: str) -> None:
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found: {path}")


def _normalize_output_format(fmt: str) -> str:
    fmt = (fmt or "png").strip().lower()
    if fmt in {"png", "jpeg", "webp"}:
        return fmt
    return "png"


def _normalize_seed(seed: int) -> int:
    try:
        seed = int(seed)
    except Exception:
        return 0
    return max(0, seed)


def _normalize_cfg_scale(value: float) -> str:
    try:
        value = float(value)
    except Exception:
        value = 7.0
    return str(value)


def _save_binary_output(content: bytes, output_format: str) -> str:
    ext = "jpg" if output_format == "jpeg" else output_format
    output_path = os.path.join(OUTPUT_DIR, f"last_result.{ext}")
    with open(output_path, "wb") as f:
        f.write(content)
    return output_path


def _raise_api_error(response: requests.Response) -> None:
    text = ""
    try:
        text = response.text
    except Exception:
        text = "<no response body>"

    if response.status_code == 402:
        raise RuntimeError(f"Stability AI Error 402: insufficient credits. Response: {text}")
    if response.status_code == 401:
        raise RuntimeError(f"Stability AI Error 401: invalid or missing API key. Response: {text}")

    raise RuntimeError(
        f"Stability AI request failed with status {response.status_code}: {text}"
    )


def generate_design(input_image_path: str, mask_path: Optional[str], prompt_data: Union[dict, str]) -> str:
    if not STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is missing.")

    _validate_file(input_image_path, "Input image")

    if mask_path:
        _validate_file(mask_path, "Mask image")

    # استخراج پرامپت مثبت و منفی (پشتیبانی از فرمت جدید)
    if isinstance(prompt_data, dict):
        positive_prompt = prompt_data.get("prompt", "").strip()
        negative_prompt = prompt_data.get("negative_prompt", "").strip()
    else:
        positive_prompt = str(prompt_data).strip()
        negative_prompt = "low quality, blurry, distorted" # پیش‌فرض در صورتی که استرینگ پاس داده شود

    if not positive_prompt:
        raise ValueError("Prompt is empty.")

    endpoint = _build_endpoint()
    output_format = _normalize_output_format(STABILITY_OUTPUT_FORMAT)

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*",
    }

    # رفع مشکل اصلی: تنظیم قدرت تغییرات (Strength) روی یک عدد استاندارد معماری
    # عدد 0.85 اجازه می‌دهد متریال و رنگ‌ها کاملاً عوض شوند اما خطوط اصلی دیوارها حفظ شود.
    optimal_strength = "0.80"

    data = {
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt, # اضافه شدن پرامپت منفی به درخواست
        "output_format": output_format,
        "seed": str(_normalize_seed(STABILITY_SEED)),
        "cfg_scale": _normalize_cfg_scale(STABILITY_CFG_SCALE),
        "strength": optimal_strength, # نادیده گرفتن تنظیمات کانفیگ برای تضمین عملکرد
    }

    files = {
        "image": open(input_image_path, "rb"),
    }

    if mask_path and os.path.exists(mask_path):
        files["mask"] = open(mask_path, "rb")

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
        _raise_api_error(response)

    return _save_binary_output(response.content, output_format)
