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
    base64_image = encode_image(input_image_path)
    
    # قدم اول: اسکن مهندسی و دقیق فرم ساختمان
    vision_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "Analyze this building with extreme architectural precision. Describe the EXACT geometric massing, the precise number and grid arrangement of windows/doors, the roof shape, and the exact camera perspective. Ignore all UI, text, and borders. Do NOT describe current materials. Give me a strict geometric blueprint in text format."
                    },
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ],
            }
        ],
        max_tokens=200
    )
    structure_desc = vision_response.choices[0].message.content

    # قدم دوم: اجبار DALL-E 3 به کپی کردن فرم
    dalle3_prompt = f"""
    Create a highly photorealistic, 8k resolution architectural visualization. 
    NO UI elements, NO borders.
    
    CRITICAL INSTRUCTION: You MUST exactly replicate this geometric structure, window grid, and camera angle:
    [BASE STRUCTURE]: {structure_desc}
    
    Now, apply the following redesign style seamlessly:
    [NEW STYLE]: {prompt}
    
    Do not change the fundamental building volume or window placement. Only change the architectural skin, style, and lighting.
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
