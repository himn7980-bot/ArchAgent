import os
import base64
from openai import OpenAI
from config import OPENAI_API_KEY, OUTPUT_DIR

client = OpenAI(api_key=OPENAI_API_KEY)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_design(input_image_path: str, mask_path: str, prompt: str) -> str:
    # ۱. پردازش تصویر با Vision (نادیده گرفتن آیکون‌های اینستاگرام و گوشی)
    base64_image = encode_image(input_image_path)
    vision_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "This image is a screenshot. Ignore ALL UI elements, text, black borders, and icons. Focus ONLY on the main building/space. Describe its architectural massing, structure, and shape in 2 simple sentences. Do not describe the UI."
                    },
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ],
            }
        ],
        max_tokens=150
    )
    structure_desc = vision_response.choices[0].message.content

    # ۲. تولید رندر تمیز و تمام‌صفحه با DALL-E 3
    dalle3_prompt = f"""
    Create a highly photorealistic, 8k resolution architectural visualization. 
    NO UI elements, NO borders, NO text. Just a pure, clean render.
    Base Building Structure: {structure_desc}. 
    User Redesign Request & Style: {prompt}. 
    Maintain the core building geometry, but completely transform the style and materials as requested.
    """

    response = client.images.generate(
        model="dall-e-3",
        prompt=dalle3_prompt.strip(),
        size="1024x1024",
        quality="standard",
        n=1,
    )

    if not getattr(response, "data", None):
        raise ValueError("No image output received from OpenAI.")

    return response.data[0].url
