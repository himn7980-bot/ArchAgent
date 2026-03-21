import os
import requests
from config import STABILITY_API_KEY, OUTPUT_DIR

os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_design(input_image_path: str, prompt: str, *args, **kwargs) -> str:
    # ۱. بررسی وجود عکس و کلید
    if not os.path.exists(input_image_path):
        raise FileNotFoundError("Input image not found.")
    
    if not STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is not set in environment variables!")

    # ۲. آماده‌سازی درخواست برای Stability AI (حالت Structure برای حفظ فرم ساختمان)
    url = "https://api.stability.ai/v2beta/stable-image/control/structure"
    
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }

    # تقویت پرامپت برای رندر واقعی و باکیفیت
    enhanced_prompt = f"Professional architectural photography, highly detailed, 8k resolution, realistic lighting and materials. {prompt}"

    files = {
        "image": open(input_image_path, "rb")
    }
    
    data = {
        "prompt": enhanced_prompt,
        "control_strength": 0.7, # عدد 0.7 یعنی 70 درصد فرم اصلی ساختمان رو دقیقا حفظ کن
        "output_format": "jpeg"
    }

    # ۳. ارسال درخواست به هوش مصنوعی
    response = requests.post(url, headers=headers, files=files, data=data)

    # ۴. ذخیره نتیجه
    if response.status_code == 200:
        output_filename = f"result_{os.path.basename(input_image_path)}.jpeg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with open(output_path, "wb") as file:
            file.write(response.content)
            
        return output_path
    else:
        raise Exception(f"Stability AI Error: {response.status_code} - {response.text}")
