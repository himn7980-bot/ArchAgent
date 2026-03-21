import os
import requests
from openai import OpenAI
from config import STABILITY_API_KEY, OPENAI_API_KEY, OUTPUT_DIR

# راه‌اندازی کلاینت OpenAI برای ترجمه
openai_client = OpenAI(api_key=OPENAI_API_KEY)

os.makedirs(OUTPUT_DIR, exist_ok=True)

def translate_to_english(text: str) -> str:
    """ترجمه متن کاربر به انگلیسی تخصصی معماری"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert architectural translator. Translate the following user request to English, focusing on architectural terms and materials. Just return the translation, nothing else."},
                {"role": "user", "content": text}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Translation failed: {e}")
        return text # اگر خطا داد، همان متن اصلی را برمی‌گرداند

def generate_design(input_image_path: str, mask_path: str, prompt: str) -> str:
    if not os.path.exists(input_image_path):
        raise FileNotFoundError(f"Input image not found: {input_image_path}")
    
    if not STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is not set in Render Environment Variables!")

    # ۱. ترجمه پرامپت فارسی به انگلیسی تخصصی
    english_prompt = translate_to_english(prompt)
    print(f"Translated Prompt: {english_prompt}")

    # ۲. آماده‌سازی درخواست برای Stability AI
    url = "https://api.stability.ai/v2beta/stable-image/control/structure"
    
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }

    # پرامپت نهایی و ترکیب‌شده
    enhanced_prompt = f"Professional architectural photography, photorealistic, highly detailed, 8k resolution, realistic lighting and premium materials. {english_prompt}"

    files = {
        "image": open(input_image_path, "rb")
    }
    
    data = {
        "prompt": enhanced_prompt,
        "control_strength": 0.7, 
        "output_format": "jpeg"
    }

    # ۳. ارسال به Stability
    response = requests.post(url, headers=headers, files=files, data=data)

    # ۴. ذخیره خروجی
    if response.status_code == 200:
        base_name = os.path.basename(input_image_path).split('.')[0]
        output_filename = f"result_{base_name}.jpeg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with open(output_path, "wb") as file:
            file.write(response.content)
            
        return output_path
    else:
        raise Exception(f"Stability AI Error: {response.status_code} - {response.text}")
