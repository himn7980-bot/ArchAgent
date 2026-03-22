import os
import threading
from PIL import Image, ImageDraw

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, MINIAPP_URL, UPLOAD_DIR
from design import generate_design
from vision import detect_scene
from voice import transcribe_voice
from texts import TEXTS
from materials import suggest_materials
from cost import estimate_cost
from stores import get_store_suggestions
from storage import create_project


def detect_message_lang(text: str) -> str:
    if not text:
        return "en"
    if any(ch in text for ch in "پچژگکی"): return "fa"
    if any(ch in text for ch in "ةؤإأيي"): return "ar"
    if any("\u0600" <= ch <= "\u06FF" for ch in text): return "fa"
    if any("\u0400" <= ch <= "\u04FF" for ch in text): return "ru"
    return "en"


def get_user_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    saved_lang = context.user_data.get("lang")
    if saved_lang: return saved_lang
    lang = (update.effective_user.language_code or "en").lower()
    if lang.startswith("fa"): return "fa"
    if lang.startswith("ar"): return "ar"
    if lang.startswith("ru"): return "ru"
    return "en"


def t(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> str:
    lang = get_user_lang(update, context)
    return TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))


def style_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)
    labels = {
        "en": {"modern": "🟦 Modern", "classic": "🏛 Classic", "minimal": "⚪ Minimal", "luxury": "✨ Luxury", "arabic": "🕌 Arabic"},
        "fa": {"modern": "🟦 مدرن", "classic": "🏛 کلاسیک", "minimal": "⚪ مینیمال", "luxury": "✨ لوکس", "arabic": "🕌 عربی"},
        "ar": {"modern": "🟦 حديث", "classic": "🏛 كلاسيكي", "minimal": "⚪ مينيمال", "luxury": "✨ فاخر", "arabic": "🕌 عربي"},
        "ru": {"modern": "🟦 Современный", "classic": "🏛 Классический", "minimal": "⚪ Минимализм", "luxury": "✨ Люкс", "arabic": "🕌 Арабский"},
    }
    l = labels.get(lang, labels["en"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(l["modern"], callback_data="style_modern"), InlineKeyboardButton(l["classic"], callback_data="style_classic")],
        [InlineKeyboardButton(l["minimal"], callback_data="style_minimal"), InlineKeyboardButton(l["luxury"], callback_data="style_luxury")],
        [InlineKeyboardButton(l["arabic"], callback_data="style_arabic")]
    ])

# --- کیبورد جدید برای آب و هوا و زمان ---
def environment_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)
    labels = {
        "en": {"day": "☀️ Day", "night": "🌙 Night", "sunset": "🌅 Sunset", "rain": "🌧 Rain", "snow": "❄️ Snow", "skip": "⏭️ Skip / Default"},
        "fa": {"day": "☀️ روز", "night": "🌙 شب", "sunset": "🌅 غروب", "rain": "🌧 بارانی", "snow": "❄️ برفی", "skip": "⏭️ بدون تغییر"},
    }
    l = labels.get(lang, labels["en"]) # اگر زبان دیگر بود پیش‌فرض انگلیسی می‌دهد
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(l["day"], callback_data="env_day"), InlineKeyboardButton(l["night"], callback_data="env_night")],
        [InlineKeyboardButton(l["sunset"], callback_data="env_sunset"), InlineKeyboardButton(l["rain"], callback_data="env_rain")],
        [InlineKeyboardButton(l["snow"], callback_data="env_snow"), InlineKeyboardButton(l["skip"], callback_data="env_skip")]
    ])


def result_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)
    labels = {
        "en": {"redo": "🔁 Regenerate", "style": "🎨 Change Style", "pay": "💰 TON Panel", "mint": "🖼 Mint NFT"},
        "fa": {"redo": "🔁 تغییر طرح", "style": "🎨 تغییر سبک", "pay": "💰 پنل TON", "mint": "🖼 مینت NFT"},
    }
    l = labels.get(lang, labels["en"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(l["redo"], callback_data="redo"), InlineKeyboardButton(l["style"], callback_data="change_style")],
        [InlineKeyboardButton(l["pay"], web_app=WebAppInfo(url=f"{MINIAPP_URL}?project_id={project_id}&user_id={update.effective_user.id}")), InlineKeyboardButton(l["mint"], callback_data="mint_hint")]
    ])


def build_prompt(space_type: str, style: str, environment: str, user_text: str) -> str:
    style_text = {
        "modern": "modern architectural style",
        "classic": "classical architectural style",
        "minimal": "minimal clean contemporary style",
        "luxury": "luxury premium style",
        "arabic": "Middle Eastern / Arabic elegant style",
    }.get(style, "professional design style")

    # ترجمه محیط به دستورات قدرتمند رندر
    env_text = {
        "day": "bright clear daylight, sunny, vivid blue sky, sharp crisp shadows",
        "night": "cinematic night time render, dark sky, glowing warm interior lights, exterior architectural lighting",
        "sunset": "golden hour lighting, sunset, warm orange and purple sky, dramatic long shadows",
        "rain": "rainy weather, wet reflective surfaces, overcast moody atmosphere, water puddles",
        "snow": "snowy winter scene, roof covered in heavy snow, cold atmosphere, soft diffused winter light",
    }.get(environment, "optimal and realistic architectural lighting")

    common_rules = f"""
User request: {user_text}
Style direction: {style_text}
Lighting & Environment: {env_text}

Rules:
- Keep the original structure and proportions
- Keep the same camera angle
- Professional architectural visualization, high quality realistic render
""".strip()

    if space_type == "interior":
        return f"Redesign this exact interior space.\n{common_rules}\nExtra: Keep room layout. Only redesign materials and lighting."
    if space_type == "exterior":
        return f"Architectural facade redesign.\n{common_rules}\nExtra: Keep exact building structure and window layout."
    if space_type == "unfinished":
        return f"Redesign this unfinished space into a completed realistic design.\n{common_rules}"
    return f"Renovate this existing space.\n{common_rules}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["lang"] = get_user_lang(update, context)
    context.user_data["awaiting_description"] = False
    await update.message.reply_text(t(update, context, "welcome"))


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo: return
    photo_file = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo_file.file_id)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    temp_jpg_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}.jpg")
    image_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}.png")
    mask_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}_mask.png")

    await tg_file.download_to_drive(temp_jpg_path)

    target_size = 1024
    with Image.open(temp_jpg_path) as img:
        img = img.convert("RGBA")
        scale = min(target_size / img.size[0], target_size / img.size[1])
        new_width, new_height = int(img.size[0] * scale), int(img.size[1] * scale)
        resized = img.resize((new_width, new_height), Image.LANCZOS)
        canvas = Image.new("RGBA", (target_size, target_size), (255, 255, 255, 255))
        canvas.paste(resized, ((target_size - new_width) // 2, (target_size - new_height) // 2), resized)
        canvas.save(image_path, "PNG")

    mask_canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 255))
    ImageDraw.Draw(mask_canvas).rectangle([50, 50, target_size - 50, target_size - 50], fill=(0, 0, 0, 0))
    mask_canvas.save(mask_path, "PNG")

    context.user_data.update({"photo_path": image_path, "mask_path": mask_path, "space_type": "interior", "style": None, "environment": None, "awaiting_description": False})

    await update.message.reply_text(t(update, context, "photo_received"))

    try: detected_scene = detect_scene(image_path)
    except Exception: detected_scene = "interior"

    context.user_data["space_type"] = detected_scene
    await update.message.reply_text(f"{t(update, context, 'scene_detected')} {detected_scene}")
    await update.message.reply_text(t(update, context, "choose_style"), reply_markup=style_keyboard(update, context))


async def handle_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    mapping = {"style_modern": "modern", "style_classic": "classic", "style_minimal": "minimal", "style_luxury": "luxury", "style_arabic": "arabic"}
    selected_style = mapping.get(query.data)

    if not selected_style: return

    context.user_data["style"] = selected_style
    
    # تغییر بزرگ: به جای درخواست مستقیم متن، اول محیط را می‌پرسیم
    lang = get_user_lang(update, context)
    msg = "حالا زمان و آب‌و‌هوا را برای رندر انتخاب کنید 🌤🌙:" if lang == "fa" else "Now select the lighting and weather 🌤🌙:"
    await query.message.reply_text(msg, reply_markup=environment_keyboard(update, context))

# --- کنترلر جدید برای مدیریت دکمه‌های آب و هوا ---
async def handle_environment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    env = query.data.replace("env_", "")
    context.user_data["environment"] = env if env != "skip" else None
    context.user_data["awaiting_description"] = True
    
    await query.message.reply_text(t(update, context, "ask_change"))


async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> None:
    photo_path = context.user_data.get("photo_path")
    mask_path = context.user_data.get("mask_path")
    style = context.user_data.get("style")
    environment = context.user_data.get("environment") # گرفتن متغیر آب و هوا
    awaiting_description = context.user_data.get("awaiting_description", False)

    if not photo_path or not os.path.exists(photo_path): return await update.message.reply_text(t(update, context, "send_photo_first"))
    if not style: return await update.message.reply_text(t(update, context, "choose_style_first"))
    if not awaiting_description: return await update.message.reply_text(t(update, context, "ask_change"))

    space_type = context.user_data.get("space_type", "interior")
    await update.message.reply_text(t(update, context, "generating"))

    try:
        # ارسال آب و هوا به پرامپت
        prompt = build_prompt(space_type, style, environment, user_text)
        generated_image = generate_design(photo_path, mask_path, prompt)

        project_id = create_project(str(update.effective_user.id), {"space_type": space_type, "style": style, "request_text": user_text, "source_image": photo_path, "generated_image": generated_image})

        if isinstance(generated_image, str) and generated_image.startswith("http"):
            await update.message.reply_photo(photo=generated_image, caption=t(update, context, "result_caption"))
        else:
            with open(generated_image, "rb") as img_file:
                await update.message.reply_photo(photo=img_file, caption=t(update, context, "result_caption"))

        context.user_data["last_generated_image"] = generated_image
        context.user_data["last_project_id"] = project_id
        context.user_data["last_style"] = style

        await update.message.reply_text(t(update, context, "wallet_prompt"), reply_markup=result_keyboard(update, context, project_id))
        context.user_data["awaiting_description"] = False

    except Exception as e:
        await update.message.reply_text(t(update, context, "ai_failed"))
        await update.message.reply_text(str(e))


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return
    user_text = update.message.text.strip()
    if not user_text: return
    context.user_data["lang"] = detect_message_lang(user_text)
    await process_request(update, context, user_text)


async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice: return
    if "photo_path" not in context.user_data: return await update.message.reply_text(t(update, context, "send_photo_first"))
    if not context.user_data.get("style"): return await update.message.reply_text(t(update, context, "choose_style_first"))

    await update.message.reply_text(t(update, context, "voice_processing"))
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    voice_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}_voice.ogg")
    tg_file = await context.bot.get_file(update.message.voice.file_id)
    await tg_file.download_to_drive(voice_path)

    try:
        transcribed_text = transcribe_voice(voice_path)
        context.user_data["lang"] = detect_message_lang(transcribed_text)
        context.user_data["awaiting_description"] = True
        await update.message.reply_text(transcribed_text)
        await process_request(update, context, transcribed_text)
    except Exception as e:
        await update.message.reply_text(t(update, context, "voice_failed"))


async def handle_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "redo":
        context.user_data["awaiting_description"] = True
        await query.message.reply_text(t(update, context, "ask_change"))
    elif data == "change_style":
        context.user_data["awaiting_description"] = False
        context.user_data["style"] = None
        context.user_data["environment"] = None
        await query.message.reply_text(t(update, context, "choose_style"), reply_markup=style_keyboard(update, context))
    elif data == "mint_hint":
        image_path = context.user_data.get("last_generated_image")
        project_id = context.user_data.get("last_project_id", "unknown")
        style = context.user_data.get("last_style", "modern")
        if not image_path or not os.path.exists(image_path): return await query.message.reply_text("❌ خطا: عکسی پیدا نشد.")
        
        await query.message.reply_text("⏳ در حال انتقال تصویر به فضای غیرمتمرکز (IPFS)...")
        try:
            from nft import create_mint_request
            mint_data = create_mint_request(project_id=project_id, owner_wallet="Pending_Wallet_Connect", title=f"ArchAgent Design - {style.capitalize()}", description="AI-generated architectural redesign.", local_image_path=image_path)
            await query.message.reply_text(f"✅ فایل‌های شما با موفقیت پین شدند!\n\n🔗 لینک متادیتا:\n{mint_data['metadata_url']}\n\n💎 لطفاً از طریق دکمه 'پنل TON' کیف پول خود را متصل کنید.")
        except Exception as e:
            await query.message.reply_text(f"❌ خطا در ساخت NFT:\n{str(e)}")


app_web = FastAPI()

@app_web.get("/")
def health(): return {"app": "ArchAgent", "ok": True}

# --- پنل Web3 ادغام شده برای اتصال کیف پول TON ---
@app_web.get("/webapp/index.html")
def webapp_page():
    html_content = """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>ArchAgent TON Panel</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
        <style>
            body { font-family: Tahoma, Arial, sans-serif; text-align: center; padding: 20px; background-color: var(--tg-theme-bg-color, #1e1e1e); color: var(--tg-theme-text-color, #ffffff); margin: 0; }
            .card { background: var(--tg-theme-secondary-bg-color, #2c2c2c); padding: 30px 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-top: 20px; }
            h2 { color: #0088cc; margin-bottom: 10px; }
            p { line-height: 1.6; font-size: 14px; opacity: 0.9; }
            #ton-connect { display: flex; justify-content: center; margin-top: 30px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>💎 پنل Web3 آرک‌ایجنت</h2>
            <p>برای دریافت مالکیت طرح معماری خود (NFT) و ارتقا به نسخه ویژه، لطفاً کیف پول TON خود را متصل کنید.</p>
            <div id="ton-connect"></div>
        </div>
        <script>
            window.Telegram.WebApp.expand();
            window.Telegram.WebApp.ready();
            const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({
                manifestUrl: 'https://raw.githubusercontent.com/ton-community/tutorials/main/03-client/test/public/tonconnect-manifest.json',
                buttonRootId: 'ton-connect'
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def run_api() -> None:
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app_web, host="0.0.0.0", port=port)

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(CallbackQueryHandler(handle_style, pattern="^style_"))
    
    # --- هندلر جدید برای دریافت کلیک‌های آب و هوا ---
    app.add_handler(CallbackQueryHandler(handle_environment, pattern="^env_"))
    
    app.add_handler(CallbackQueryHandler(handle_actions, pattern="^(redo|change_style|mint_hint)$"))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, description))
    print("ArchAgent running...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    threading.Thread(target=run_api, daemon=True).start()
    main()
