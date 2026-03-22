import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# OpenAI (analysis only)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4.1-mini").strip()
TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe").strip()

# Stability AI (render only)
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "").strip()
STABILITY_API_HOST = os.getenv("STABILITY_API_HOST", "https://api.stability.ai").rstrip("/")
STABILITY_IMAGE_MODEL = os.getenv("STABILITY_IMAGE_MODEL", "stable-image/edit/inpaint").strip()
STABILITY_OUTPUT_FORMAT = os.getenv("STABILITY_OUTPUT_FORMAT", "png").strip().lower()
STABILITY_SEED = int(os.getenv("STABILITY_SEED", "0"))
STABILITY_CFG_SCALE = float(os.getenv("STABILITY_CFG_SCALE", "7"))
STABILITY_STRENGTH = float(os.getenv("STABILITY_STRENGTH", "0.65"))

# App URLs
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")
MINIAPP_URL = os.getenv("MINIAPP_URL", f"{APP_BASE_URL}/webapp/index.html").strip()

# TON / payments
TON_MERCHANT_ADDRESS = os.getenv("TON_MERCHANT_ADDRESS", "").strip()
TON_API_BASE = os.getenv("TON_API_BASE", "https://tonapi.io").rstrip("/")
TON_API_KEY = os.getenv("TON_API_KEY", "").strip()

# NFT / admin
NFT_COLLECTION_ADDRESS = os.getenv("NFT_COLLECTION_ADDRESS", "").strip()
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "CHANGE_ME").strip()

# App settings
FREE_RENDERS = int(os.getenv("FREE_RENDERS", "3"))

# Storage
DATA_DIR = os.getenv("DATA_DIR", "data").strip()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "user_uploads").strip()
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "ai_outputs").strip()

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing.")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing.")

if not STABILITY_API_KEY:
    raise ValueError("STABILITY_API_KEY is missing.")
