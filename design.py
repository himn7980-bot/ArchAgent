import os
import requests
from config import OUTPUT_DIR

# دریافت کلید مستقیماً از متغیرهای محیطی سرور
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "").strip()

# اطمینان از وجود پوشه خروجی
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_design(input_image_path: str, mask_path: str, prompt: str) -> str:
    # ۱. بررسی‌های اولیه
    if not os.path.exists(input_image_path):
        raise FileNotFoundError(f"Input image not found: {input_image_path}")
    
    if not STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is not set in Render Environment Variables!")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt is empty.")

    # ۲. آماده‌سازی درخواست برای Stability AI (مدل Structure)
    url = "https://api.stability.ai/v2beta/stable-image/control/structure"
    
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }

    # تقویت پرامپت برای دریافت بالاترین کیفیت معماری
    enhanced_prompt = f"Professional architectural photography, photorealistic, highly detailed, 8k resolution, realistic lighting and premium materials. {prompt.strip()}"

    # باز کردن عکس اصلی (دیگر نیازی به ارسال فایل ماسک به این API نیست)
    files = {
        "image": open(input_image_path, "rb")
    }
    
    data = {
        "prompt": enhanced_prompt,
        "control_strength": 0.7,  # این عدد طلایی است: ۷۰٪ فرم را حفظ می‌کند و ۳۰٪ دستش برای تغییر متریال باز است
        "output_format": "jpeg"
    }

    # ۳. ارسال عکس و متن به سرور Stability
    response = requests.post(url, headers=headers, files=files, data=data)

    # ۴. ذخیره و برگرداندن عکس خروجی
    if response.status_code == 200:
        base_name = os.path.basename(input_image_path).split('.')[0]
        output_filename = f"result_{base_name}.jpeg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with open(output_path, "wb") as file:
            file.write(response.content)
            
        return output_path
    else:
        raise Exception(f"Stability AI Error: {response.status_code} - {response.text}")
