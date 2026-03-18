import os
import base64
from openai import OpenAI
from config import OPENAI_API_KEY, IMAGE_MODEL, IMAGE_SIZE, OUTPUT_DIR

client = OpenAI(api_key=OPENAI_API_KEY)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_design(input_image_path: str, prompt: str) -> str:
    with open(input_image_path, "rb") as image_file:
        result = client.images.edit(
            model=IMAGE_MODEL,
            image=image_file,
            prompt=prompt,
            size=IMAGE_SIZE,
        )

    image_data = result.data[0]

    if getattr(image_data, "url", None):
        return image_data.url

    if getattr(image_data, "b64_json", None):
        output_path = os.path.join(OUTPUT_DIR, "last_result.png")
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_data.b64_json))
        return output_path

    raise ValueError("No image output received from OpenAI.")