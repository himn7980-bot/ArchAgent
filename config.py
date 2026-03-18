import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gpt-image-1")
IMAGE_SIZE = os.getenv("IMAGE_SIZE", "1536x1024")
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4.1-mini")
TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
MINIAPP_URL = os.getenv("MINIAPP_URL", f"{APP_BASE_URL}/webapp/index.html")

TON_MERCHANT_ADDRESS = os.getenv("TON_MERCHANT_ADDRESS", "")
TON_API_BASE = os.getenv("TON_API_BASE", "https://tonapi.io")
TON_API_KEY = os.getenv("TON_API_KEY", "")

NFT_COLLECTION_ADDRESS = os.getenv("NFT_COLLECTION_ADDRESS", "")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "CHANGE_ME")

FREE_RENDERS = 3
SUPPORTED_LANGS = ["en", "fa", "ar", "ru"]

DATA_DIR = "data"
UPLOAD_DIR = "user_uploads"
OUTPUT_DIR = "ai_outputs"