import os
import base64
from openai import OpenAI
from config import OPENAI_API_KEY, IMAGE_MODEL, OUTPUT_DIR

# راه‌اندازی کلاینت OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# اطمینان از وجود پوشه خروجی‌ها
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_design(input_image_path: str, mask_path: str, prompt: str) -> str:
    # ۱. بررسی وجود فایل‌ها
    if not os.path.exists(input_image_path):
        raise FileNotFoundError(f"Input image not found: {input_image_path}")
    if not os.path.exists(mask_path):
        raise FileNotFoundError(f"Mask image not found: {mask_path}")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt is empty.")

    # ۲. ارسال عکس و ماسک به API
    with open(input_image_path, "rb") as image_file, open(mask_path, "rb") as mask_file:
        result = client.images.edit(
            model=IMAGE_MODEL,  # معمولاً dall-e-2
            image=image_file,
            mask=mask_file,
            prompt=prompt.strip(),
            size="1024x1024",
        )

    # ۳. اعتبارسنجی خروجی
    if not getattr(result, "data", None):
        raise ValueError("No image output received from OpenAI.")

    image_data = result.data[0]

    # ۴. استخراج نتیجه (لینک یا فایل)
    if getattr(image_data, "url", None):
        return image_data.url

    if getattr(image_data, "b64_json", None):
        # ساخت یک اسم یکتا برای فایل خروجی تا فایل‌های قبلی پاک نشوند
        base_name = os.path.basename(input_image_path)
        output_path = os.path.join(OUTPUT_DIR, f"result_{base_name}")
        
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_data.b64_json))
        return output_path

    raise ValueError("No valid image data (url or b64_json) received from OpenAI.")
