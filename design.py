import os
import base64
from openai import OpenAI
from config import OPENAI_API_KEY, OUTPUT_DIR

client = OpenAI(api_key=OPENAI_API_KEY)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_design(input_image_path: str, mask_path: str, prompt: str) -> str:
    # بررسی وجود فایل‌های عکس اصلی و ماسک
    if not os.path.exists(input_image_path) or not os.path.exists(mask_path):
        raise FileNotFoundError("Input image or mask not found.")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt is empty.")

    # استفاده از مدل dall-e-2 برای ویرایش دقیق (Inpainting) روی فرم قبلی
    with open(input_image_path, "rb") as image_file, open(mask_path, "rb") as mask_file:
        result = client.images.edit(
            model="dall-e-2",
            image=image_file,
            mask=mask_file,
            prompt=f"Professional architectural redesign, highly realistic, 8k resolution. {prompt.strip()}",
            size="1024x1024",
        )

    if not getattr(result, "data", None):
        raise ValueError("No image output received from OpenAI.")

    image_data = result.data[0]

    # برگرداندن لینک تصویر خروجی
    if getattr(image_data, "url", None):
        return image_data.url

    # ذخیره فایل در صورت دریافت Base64
    if getattr(image_data, "b64_json", None):
        output_path = os.path.join(OUTPUT_DIR, "last_result.png")
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_data.b64_json))
        return output_path

    raise ValueError("No valid image output received from OpenAI.")
