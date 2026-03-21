import os
from dotenv import load_dotenv

load_dotenv()

# =========================
# Core tokens and API keys
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "").strip()
PINATA_API_KEY = os.getenv("PINATA_API_KEY", "").strip()
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY", "").strip()

# =========================
# OpenAI models
# =========================
# For image editing in your current setup, Render/OpenAI is expecting dall-e-2
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "dall-e-2").strip()
IMAGE_SIZE = os.getenv("IMAGE_SIZE", "1024x1024").strip()

# Vision and transcription models
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4.1-mini").strip()
TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe").strip()

# =========================
# App URLs
# =========================
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")
MINIAPP_URL = os.getenv("MINIAPP_URL", f"{APP_BASE_URL}/webapp/index.html").strip()

# =========================
# TON / payments
# =========================
TON_MERCHANT_ADDRESS = os.getenv("TON_MERCHANT_ADDRESS", "").strip()
TON_API_BASE = os.getenv("TON_API_BASE", "https://tonapi.io").rstrip("/")
TON_API_KEY = os.getenv("TON_API_KEY", "").strip()

# =========================
# NFT / admin
# =========================
NFT_COLLECTION_ADDRESS = os.getenv("NFT_COLLECTION_ADDRESS", "").strip()
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "CHANGE_ME").strip()

# =========================
# App limits and settings
# =========================
FREE_RENDERS = int(os.getenv("FREE_RENDERS", "3"))
SUPPORTED_LANGS = ["en", "fa", "ar", "ru"]

# =========================
# Storage paths
# =========================
DATA_DIR = os.getenv("DATA_DIR", "data").strip()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "user_uploads").strip()
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "ai_outputs").strip()

# =========================
# Basic validation
# =========================
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing.")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing.")
