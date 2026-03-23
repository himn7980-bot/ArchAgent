import os
import asyncio
import threading
from PIL import Image

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.constants import ChatAction
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
from vision import detect_scene, translate_request_to_english
from voice import transcribe_voice
from texts import TEXTS
from materials import suggest_materials
from cost import estimate_cost
from stores import get_store_suggestions
from storage import create_project
from prompt_engine import PromptEngine


# =========================
# Language & Helpers
# =========================

def detect_message_lang(text: str) -> str:
    if not text: return "en"
    if any(ch in text for ch in "پچژگکی"): return "fa"
    if any(ch in text for ch in "ةؤإأيي"): return "ar"
    if any("\u0400" <= ch <= "\u04FF" for ch in text): return "ru"
    return "en"


def get_user_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    saved = context.user_data.get("lang")
    if saved: return saved
    lang = (update.effective_user.language_code or "en").lower()
    if lang.startswith("fa"): return "fa"
    if lang.startswith("ar"): return "ar"
    if lang.startswith("ru"): return "ru"
    return "en"


def t(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    lang = get_user_lang(update, context)
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)


def reset_user_flow(context):
    lang = context.user_data.get("lang")
    context.user_data.clear()
    if lang:
        context.user_data["lang"] = lang


# =========================
# Keyboards
# =========================

def style_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟦 Modern", callback_data="style_modern"), InlineKeyboardButton("🏛 Classic", callback_data="style_classic")],
        [InlineKeyboardButton("⚪ Minimal", callback_data="style_minimal"), InlineKeyboardButton("✨ Luxury", callback_data="style_luxury")],
        [InlineKeyboardButton("🕌 Arabic", callback_data="style_arabic")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])


def time_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("☀️ Day", callback_data="time_day"), InlineKeyboardButton("🌙 Night", callback_data="time_night")],
        [InlineKeyboardButton("🌅 Sunset", callback_data="time_sunset"), InlineKeyboardButton("⏭ Skip", callback_data="time_skip")]
    ])


def weather_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌤 Clear", callback_data="weather_clear"), InlineKeyboardButton("🌧 Rain", callback_data="weather_rain")],
        [InlineKeyboardButton("❄ Snow", callback_data="weather_snow"), InlineKeyboardButton("⏭ Skip", callback_data="weather_skip")]
    ])


def result_keyboard(update, project_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔁 Regenerate", callback_data="redo"),
            InlineKeyboardButton("🎨 Change Style", callback_data="change_style"),
        ],
        [
            InlineKeyboardButton(
                "💰 TON Panel",
                web_app=WebAppInfo(url=f"{MINIAPP_URL}?project_id={project_id}&user_id={update.effective_user.id}")
            ),
            InlineKeyboardButton("🖼 Mint NFT", callback_data="mint_hint"),
        ],
    ])


# =========================
# Core AI Process
# =========================

async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    data = context.user_data
    
    if not data.get("photo_path") or not os.path.exists(data["photo_path"]):
        return await update.message.reply_text("⚠️ Please send a photo first.")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text(t(update, context, "generating"))

    try:
        english_request = translate_request_to_english(user_text)

        # ساخت پرامپت (حالا یک دیکشنری شامل positive و negative برمی‌گرداند)
        prompt_data = PromptEngine.build_final_prompt(
            space_type=data.get("space_type", "interior"),
            style=data.get("style", "modern"),
            time_of_day=data.get("time_of_day"),
            weather=data.get("weather"),
            user_text=english_request,
        )

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)

        # تولید تصویر (سازگار شده با پرامپت دیکشنری و تغییرات strength در فایل design.py)
        generated = generate_design(data["photo_path"], None, prompt_data)

        # ذخیره پروژه
        project_id = create_project(
            str(update.effective_user.id),
            {
                "generated_image": generated,
                "prompt": str(prompt_data) # تبدیل به استرینگ برای ذخیره امن در دیتابیس
            }
        )

        # ارسال خروجی
        if generated.startswith("http"):
            await update.message.reply_photo(generated)
        else:
            with open(generated, "rb") as img:
                await update.message.reply_photo(img)

        # اطلاعات تکمیلی
        materials = suggest_materials(data["space_type"], data["style"])
        if materials: await update.message.reply_text("\n".join(materials))

        cost = estimate_cost(data["space_type"], data["style"])
        if cost: await update.message.reply_text(str(cost))

        stores = get_store_suggestions(data["space_type"], data["style"])
        if stores: await update.message.reply_text("\n".join(stores))

        # آپدیت استیت کاربر
        context.user_data.update({
            "awaiting_description": False,
            "last_project_id": project_id,
            "last_generated_image": generated,
            "last_request_text": user_text
        })

        await update.message.reply_text(
            t(update, context, "wallet_prompt"),
            reply_markup=result_keyboard(update, project_id),
        )

    except Exception as e:
        print(f"Error in process_request: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# =========================
# Handlers
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user_flow(context)
    await update.message.reply_text(t(update, context, "welcome"))


def process_image_sync(temp_path: str, image_path: str):
    """تابع همگام برای ریسایز کردن تصویر بدون مسدود کردن ربات"""
    with Image.open(temp_path) as img:
        img = img.convert("RGBA")
        scale = min(1024 / img.size[0], 1024 / img.size[1])
        new = (int(img.size[0] * scale), int(img.size[1] * scale))
        resized = img.resize(new, Image.LANCZOS)
        canvas = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        canvas.paste(resized, ((1024 - new[0]) // 2, (1024 - new[1]) // 2))
        canvas.save(image_path)
    if os.path.exists(temp_path):
        os.remove(temp_path)


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)

    photo_file = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo_file.file_id)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    image_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}.png")
    temp = image_path + ".temp"

    await tg_file.download_to_drive(temp)

    # پردازش غیرمسدودکننده تصویر
    await asyncio.to_thread(process_image_sync, temp, image_path)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        scene = detect_scene(image_path)
    except:
        scene = "interior"

    context.user_data.update({
        "photo_path": image_path,
        "space_type": scene,
        "style": None,
        "time_of_day": None,
        "weather": None,
        "awaiting_description": False,
    })

    await update.message.reply_text(f"Scene detected: {scene}\nChoose style:", reply_markup=style_keyboard())


async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("photo_path") or not os.path.exists(context.user_data["photo_path"]):
        return await update.message.reply_text("⚠️ Please send a photo first.")

    path = os.path.join(UPLOAD_DIR, f"voice_{update.effective_user.id}.ogg")
    
    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        await file.download_to_drive(path)

        transcription = transcribe_voice(path)
        text = transcription.get("text", "")
        
        if not text:
            return await update.message.reply_text("Could not understand the voice.")
            
        await update.message.reply_text(f"🎤 You said: {text}")
        context.user_data["awaiting_description"] = True
        await process_request(update, context, text)
        
    except Exception as e:
        print(f"Voice error: {e}")
        await update.message.reply_text("Error processing voice message.")
    finally:
        if os.path.exists(path):
            os.remove(path)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["lang"] = detect_message_lang(text)

    if context.user_data.get("awaiting_description"):
        if not context.user_data.get("photo_path") or not os.path.exists(context.user_data["photo_path"]):
            return await update.message.reply_text("⚠️ Please send a photo first.")
        await process_request(update, context, text)


async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "restart":
        reset_user_flow(context)
        await query.message.reply_text("🔄 Restarted. Please send a new photo.")
        return

    if data == "cancel":
        context.user_data["awaiting_description"] = False
        await query.message.reply_text("❌ Cancelled. You can send a new photo anytime.")
        return

    if data.startswith("style_"):
        context.user_data["style"] = data.replace("style_", "")
        await query.message.reply_text("Choose time of day:", reply_markup=time_keyboard())

    elif data.startswith("time_"):
        context.user_data["time_of_day"] = data.replace("time_", "") if "skip" not in data else None
        await query.message.reply_text("Choose weather:", reply_markup=weather_keyboard())

    elif data.startswith("weather_"):
        context.user_data["weather"] = data.replace("weather_", "") if "skip" not in data else None
        context.user_data["awaiting_description"] = True
        await query.message.reply_text("Please describe what you want to change (e.g., 'Blue cabinets, wood floor'):")

    elif data == "redo":
        last_request = context.user_data.get("last_request_text", "")
        await query.message.reply_text("🔁 Regenerating your design...")
        await process_request(update, context, last_request)

    elif data == "change_style":
        await query.message.reply_text("Choose a new style:", reply_markup=style_keyboard())

    elif data == "mint_hint":
        project_id = context.user_data.get("last_project_id")
        img_path = context.user_data.get("last_generated_image")
        if not project_id or not img_path:
            return await query.message.reply_text("❌ No recent project found to mint.")
            
        try:
            from nft import create_mint_request
            await query.message.reply_text("⏳ Uploading to IPFS...")
            mint_data = create_mint_request(project_id, "Pending", "ArchAgent", "AI Design on TON", img_path)
            await query.message.reply_text(f"✅ Pinned! Connect your wallet in the TON Panel to complete minting.")
        except Exception as e:
            print(f"NFT error: {e}")
            await query.message.reply_text("❌ Error uploading NFT.")


# =========================
# FastAPI & UptimeRobot
# =========================

app_web = FastAPI()

# نقطه‌ی ایده‌آل برای UptimeRobot
@app_web.get("/")
@app_web.get("/ping")
def health():
    return {"ArchAgent": "running", "status": "200 OK"}

@app_web.get("/webapp/index.html")
def webapp():
    return HTMLResponse("<h2>💎 TON Panel</h2><p>Connect your wallet to Mint NFTs or Pay for Pro features.</p>")


def run_web():
    uvicorn.run(
        app_web,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        log_level="warning" # کاهش لاگ‌های اضافی سرور وب
    )


# =========================
# Main Setup
# =========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    app.add_handler(CallbackQueryHandler(handle_callbacks))

    # اجرای وب‌سرور برای پاسخ به UptimeRobot و مینی‌اپ در پس‌زمینه
    threading.Thread(target=run_web, daemon=True).start()

    print("🚀 ArchAgent is running and ready for UptimeRobot!")

    app.run_polling()


if __name__ == "__main__":
    main()
