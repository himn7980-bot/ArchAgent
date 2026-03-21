import os
import requests
from openai import OpenAI
from config import STABILITY_API_KEY, OPENAI_API_KEY, OUTPUT_DIR

# راه‌اندازی کلاینت OpenAI برای ترجمه و تقویت پرامپت
openai_client = OpenAI(api_key=OPENAI_API_KEY)

os.makedirs(OUTPUT_DIR, exist_ok=True)

def translate_and_expand_prompt(text: str) -> str:
    """ترجمه متن کاربر به انگلیسی تخصصی و تقویت آن برای رندر معماری باکیفیت"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
You are an expert architectural visualization prompt engineer. Your job is to translate and expand the following user request into a highly detailed, technical, professional architectural visualization prompt (8k, photorealistic, cinematic). 

CRUCIAL INSTRUCTION: Guarantee the preservation of the original geometric massing, camera angle, and exact grid layout of the reference building. 
Do not description current materials. Describe the new desired textures and materials (e.g., specific white travertine stone, textured Dutch speckled brick, premium high-performance curtain wall glass) with detailed language.
Just return the translation and expanded prompt, nothing else.
""".strip()},
                {"role": "user", "content": text}
            ],
            max_tokens=250
        )
        expanded_prompt = response.choices[0].message.content.strip()
        print(f"Original Text: {text}")
        print(f"Expanded Prompt: {expanded_prompt}")
        return expanded_prompt
    except Exception as e:
        print(f"Translation/Expansion failed: {e}")
        return text # اگر خطا داد، همان متن اصلی را برمی‌گرداند


def generate_design(input_image_path: str, mask_path: str, prompt: str) -> str:
    if not os.path.exists(input_image_path):
        raise FileNotFoundError(f"Input image not found: {input_image_path}")
    
    if not STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is not set in Render Environment Variables!")

    # ۱. ترجمه و تقویت پرامپت (دو جهش فنی: ترجمه + افزودن جزئیات معماری لوکس)
    english_enhanced_prompt = translate_and_expand_prompt(prompt)

    # ۲. آماده‌سازی درخواست برای Stability AI
    url = "https://api.stability.ai/v2beta/stable-image/control/structure"
    
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }

    # تقویت پرامپت نهایی با کلمات کلیدی رندرهای فوق‌حرفه‌ای معماری
    final_prompt = f"Professional architectural photography, ultra-realistic, highly detailed, 8k resolution, cinematic lighting, premium textures, advanced architectural materials. {english_enhanced_prompt}"

    files = {
        "image": open(input_image_path, "rb")
    }
    
    data = {
        "prompt": final_prompt,
        "control_strength": 0.9, # جهش فنی: افزایش پایبندی به فرم به ۹۰٪ (۱۰۰٪ به رفرنس نزدیک‌تر)
        "output_format": "jpeg"
    }

    # ۳. ارسال به هوش مصنوعی (مرحله ای که داورها انگشت‌به‌دهان می‌مانند)
    response = requests.post(url, headers=headers, files=files, data=data)

    # ۴. ذخیره خروجی
    if response.status_code == 200:
        base_name = os.path.basename(input_image_path).split('.')[0]
        output_filename = f"result_hd_{base_name}.jpeg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with open(output_path, "wb") as file:
            file.write(response.content)
            
        return output_path
    else:
        raise Exception(f"Stability AI Error: {response.status_code} - {response.text}")
