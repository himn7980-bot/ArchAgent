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
    OUTPUT_DIR,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def _build_endpoint() -> str:
    # برای معماری، این آدرس باید به control/structure ختم شود
    model_path = STABILITY_IMAGE_MODEL.strip().lstrip("/")
    return f"{STABILITY_API_HOST}/v2beta/{model_path}"


def _validate_file(path: str, label: str) -> None:
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found: {path}")


def _normalize_output_format(fmt: str) -> str:
    fmt = (fmt or "jpeg").strip().lower()
    if fmt in {"png", "jpeg", "webp"}:
        return fmt
    return "jpeg"


def _normalize_seed(seed: int) -> int:
    try:
        seed = int(seed)
    except Exception:
        return 0
    return max(0, seed)


def _save_binary_output(content: bytes, output_format: str) -> str:
    ext = "jpg" if output_format == "jpeg" else output_format
    output_path = os.path.join(OUTPUT_DIR, f"last_result.{ext}")
    with open(output_path, "wb") as f:
        f.write(content)
    return output_path


def _raise_api_error(response: requests.Response) -> None:
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

    # استخراج پرامپت مثبت و منفی
    if isinstance(prompt_data, dict):
        positive_prompt = prompt_data.get("prompt", "").strip()
        negative_prompt = prompt_data.get("negative_prompt", "").strip()
    else:
        positive_prompt = str(prompt_data).strip()
        negative_prompt = "cartoon, low quality, bad architecture, warped lines, messy geometry, flat lighting"

    if not positive_prompt:
        raise ValueError("Prompt is empty.")

    endpoint = _build_endpoint()
    output_format = _normalize_output_format(STABILITY_OUTPUT_FORMAT)

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*",
    }

    # عدد جادویی برای معماری: 0.65 تا 0.70
    # این عدد به هوش مصنوعی می‌گوید 65٪ به خطوط عکس وفادار باش و 35٪ متریال و رنگ‌ها را عوض کن.
    optimal_strength = 0.65

    data = {
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "output_format": output_format,
        "seed": str(_normalize_seed(STABILITY_SEED)),
        # ارسال هر دو پارامتر تا مستقل از نوع Endpoint (Structure یا Img2Img) درست کار کند
        "strength": str(optimal_strength), 
        "control_strength": str(optimal_strength),
    }

    files = {
        "image": open(input_image_path, "rb"),
    }

    # مدل Control Structure معمولاً ماسک نمی‌گیرد، اما برای Img2Img ارسالش مشکلی ندارد
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
