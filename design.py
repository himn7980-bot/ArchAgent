import os
import base64
from openai import OpenAI

from config import OPENAI_API_KEY, IMAGE_MODEL, IMAGE_SIZE, OUTPUT_DIR

client = OpenAI(api_key=OPENAI_API_KEY)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save_b64_image(b64_data: str, output_path: str) -> str:
    image_bytes = base64.b64decode(b64_data)
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    return output_path


def _normalize_size(size: str) -> str:
    allowed_sizes = {"256x256", "512x512", "1024x1024"}
    if size in allowed_sizes:
        return size
    return "1024x1024"


def generate_design(input_image_path: str, mask_path: str, prompt: str) -> str:
    """
    Generate an edited architectural image based on:
    - source image
    - optional mask
    - final prompt

    Returns:
        - URL string if API returns a URL
        - local PNG path if API returns base64 image
    """

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing.")

    if not input_image_path or not os.path.exists(input_image_path):
        raise FileNotFoundError(f"Input image not found: {input_image_path}")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt is empty.")

    if not IMAGE_MODEL:
        raise ValueError("IMAGE_MODEL is missing.")

    image_size = _normalize_size(IMAGE_SIZE)

    output_path = os.path.join(OUTPUT_DIR, "last_result.png")

    # اگر ماسک وجود داشت و معتبر بود، از edit استفاده می‌کنیم
    # اگر نبود، از generation fallback استفاده می‌کنیم
    use_mask = bool(mask_path and os.path.exists(mask_path))

    try:
        if use_mask:
            with open(input_image_path, "rb") as image_file, open(mask_path, "rb") as mask_file:
                result = client.images.edit(
                    model=IMAGE_MODEL,
                    image=image_file,
                    mask=mask_file,
                    prompt=prompt.strip(),
                    size=image_size,
                )
        else:
            # fallback اگر mask موجود نبود
            with open(input_image_path, "rb") as image_file:
                result = client.images.edit(
                    model=IMAGE_MODEL,
                    image=image_file,
                    prompt=prompt.strip(),
                    size=image_size,
                )

    except Exception as e:
        raise RuntimeError(f"OpenAI image edit failed: {str(e)}")

    if not getattr(result, "data", None):
        raise ValueError("No image data returned from OpenAI.")

    first_item = result.data[0]

    # اگر URL برگشت
    if getattr(first_item, "url", None):
        return first_item.url

    # اگر base64 برگشت
    if getattr(first_item, "b64_json", None):
        return _save_b64_image(first_item.b64_json, output_path)

    raise ValueError("OpenAI returned no usable image output.")
