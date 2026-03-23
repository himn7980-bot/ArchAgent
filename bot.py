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

# وارد کردن تمام ماژول‌های پروژه
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

# --- ۱. توابع کمکی و زبان ---

def detect_message_lang(text: str) -> str:
    if not text: return "en"
    if any(ch in text for ch in "پچژگکی"): return "fa"
    if any(ch in text for ch in "ةؤإأيي"): return "ar"
    if any("\u0600" <= ch <= "\u06FF" for ch in text): return "fa"
    return "en"

def get_user_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    saved_lang = context.user_data.get("lang")
    if saved_lang: return saved_lang
    lang = (update.effective_user.language_code or "en").lower()
    if lang.startswith("fa"): return "fa"
    if lang.startswith("ar"): return "ar"
    return "en"

def t(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> str:
    lang = get_user_lang(update, context)
    return TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))

def normalize_space_type(space_type: str, user_text: str) -> str:
    text = (user_text or "").lower()
    if any(k in text for k in ["kitchen", "آشپزخانه", "مطبخ"]): return "kitchen"
    if any(k in text for k in ["bathroom", "حمام", "سرویس"]): return "bathroom"
    if any(k in text for k in ["living", "پذیرایی", "نشیمن"]): return "living_room"
    return space_type if space_type in ["exterior", "unfinished"] else "interior"

# --- ۲. کیبوردهای هوشمند ---

def style_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)
    l = {"fa": {"m": "🟦 مدرن", "c": "🏛 کلاسیک", "mn": "⚪ مینیمال", "lx": "✨ لوکس", "ar": "🕌 عربی"},
         "en": {"m": "🟦 Modern", "c": "🏛 Classic", "mn": "⚪ Minimal", "lx": "✨ Luxury", "ar": "🕌 Arabic"}}.get(lang, {"m": "🟦 Modern", "c": "🏛 Classic", "mn": "⚪ Minimal", "lx": "✨ Luxury", "ar": "🕌 Arabic"})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(l["m"], callback_data="style_modern"), InlineKeyboardButton(l["c"], callback_data="style_classic")],
        [InlineKeyboardButton(l["mn"], callback_data="style_minimal"), InlineKeyboardButton(l["lx"], callback_data="style_luxury")],
        [InlineKeyboardButton(l["ar"], callback_data="style_arabic")]
    ])

def time_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)
    l = {"fa": {"d": "☀️ روز", "n": "🌙 شب", "s": "🌅 غروب", "k": "⏭️ رد شدن"},
         "en": {"d": "☀️ Day", "n": "🌙 Night", "s": "🌅 Sunset", "k": "⏭️ Skip"}}.get(lang, {"d": "☀️ Day", "n": "🌙 Night", "s": "🌅 Sunset", "k": "⏭️ Skip"})
    return InlineKeyboardMarkup([[InlineKeyboardButton(l["d"], callback_data="time_day"), InlineKeyboardButton(l["n"], callback_data="time_night")],
                                 [InlineKeyboardButton(l["s"], callback_data="time_sunset"), InlineKeyboardButton(l["k"], callback_data="time_skip")]])

def weather_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)
    l = {"fa": {"c": "🌤 صاف", "r": "🌧 بارانی", "s": "❄️ برفی", "k": "⏭️ رد شدن"},
         "en": {"c": "🌤 Clear", "r": "🌧 Rain", "s": "❄️ Snow", "k": "⏭️ Skip"}}.get(lang, {"c": "🌤 Clear", "r": "🌧 Rain", "s": "❄️ Snow", "k": "⏭️ Skip"})
    return InlineKeyboardMarkup([[InlineKeyboardButton(l["c"], callback_data="weather_clear"), InlineKeyboardButton(l["r"], callback_data="weather_rain")],
                                 [InlineKeyboardButton(l["s"], callback_data="weather_snow"), InlineKeyboardButton(l["k"], callback_data="weather_skip")]])

def result_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)
    l = {"fa": {"re": "🔁 تغییر طرح", "st": "🎨 تغییر سبک", "pa": "💰 پنل TON", "mi": "🖼 مینت NFT"},
         "en": {"re": "🔁 Regenerate", "st": "🎨 Change Style", "pa": "💰 TON Panel", "mi": "🖼 Mint NFT"}}.get(lang, {"re": "🔁 Regenerate", "st": "🎨 Change Style", "pa": "💰 TON Panel", "mi": "🖼 Mint NFT"})
    return InlineKeyboardMarkup([[InlineKeyboardButton(l["re"], callback_data="redo"), InlineKeyboardButton(l["st"], callback_data="change_style")],
                                 [InlineKeyboardButton(l["pa"], web_app=WebAppInfo(url=f"{MINIAPP_URL}?project_id={project_id}&user_id={update.effective_user.id}")),
                                  InlineKeyboardButton(l["mi"], callback_data="mint_hint")]])

# --- ۳. پردازشگر اصلی (Core Engine) ---

async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> None:
    data = context.user_data
    if not data.get("photo_path"): 
        return await update.message.reply_text(t(update, context, "send_photo_first"))
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    await update.message.reply_text(t(update, context, "generating"))

    try:
        english_request = translate_request_to_english(user_text)
        space_type = normalize_space_type(data["space_type"], user_text)
        
        prompt = PromptEngine.build_final_prompt(space_type, data["style"], data.get("time_of_day"), data.get("weather"), english_request)
        generated_image = generate_design(data["photo_path"], None, prompt)
        
        project_id = create_project(str(update.effective_user.id), {
            "space_type": space_type, "style": data["style"], "request_text": user_text, "generated_image": generated_image
        })

        with open(generated_image, "rb") as img:
            await update.message.reply_photo(photo=img, caption=t(update, context, "result_caption"))

        materials = suggest_materials(space_type, data["style"])
        if materials: await update.message.reply_text(f"🧱 {t(update, context, 'materials_title')}\n- " + "\n- ".join(materials))
        
        cost = estimate_cost(space_type, data["style"])
        if cost: await update.message.reply_text(f"💰 {t(update, context, 'cost_title')}\n{cost}")
        
        stores = get_store_suggestions(space_type, data["style"])
        if stores: await update.message.reply_text(f"🏪 {t(update, context, 'stores_title')}\n- " + "\n- ".join(stores))

        data.update({"last_generated_image": generated_image, "last_project_id": project_id, "last_style": data["style"], "awaiting_description": False})
        await update.message.reply_text(t(update, context, "wallet_prompt"), reply_markup=result_keyboard(update, context, project_id))

    except Exception as e:
        print(f"Error in process_request: {e}")
        await update.message.reply_text(f"❌ {t(update, context, 'ai_failed')}")

# --- ۴. هندلرهای ورودی ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /start"""
    context.user_data.clear() # پاک کردن حافظه قبلی کاربر
    welcome_text = t(update, context, "welcome") if hasattr(TEXTS, "welcome") else "سلام! لطفاً یک عکس از فضای مورد نظرت ارسال کن تا طراحیش کنیم. 📸"
    await update.message.reply_text(welcome_text)

def process_image_sync(temp_path: str, image_path: str):
    """تابع همگام برای پردازش تصویر با Pillow (برای اجرا در Thread جداگانه)"""
    with Image.open(temp_path) as img:
        img = img.convert("RGBA")
        scale = min(1024/img.size[0], 1024/img.size[1])
        new_size = (int(img.size[0]*scale), int(img.size[1]*scale))
        resized = img.resize(new_size, Image.LANCZOS)
        canvas = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        canvas.paste(resized, ((1024-new_size[0])//2, (1024-new_size[1])//2), resized)
        canvas.save(image_path, "PNG")
    
    # حذف فایل موقت
    if os.path.exists(temp_path):
        os.remove(temp_path)

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo_file = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo_file.file_id)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    image_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}.png")
    temp_path = image_path + ".temp"
    
    await tg_file.download_to_drive(temp_path)
    
    # پردازش تصویر در پس‌زمینه (بدون فریز شدن ربات)
    await asyncio.to_thread(process_image_sync, temp_path, image_path)

    try: 
        detected = detect_scene(image_path)
    except Exception as e: 
        print(f"Vision error: {e}")
        detected = "interior"
    
    context.user_data.update({"photo_path": image_path, "space_type": detected, "awaiting_description": False})
    await update.message.reply_text(f"{t(update, context, 'photo_received')}\n🔍 {t(update, context, 'scene_detected')} {detected}")
    await update.message.reply_text(t(update, context, "choose_style"), reply_markup=style_keyboard(update, context))

async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("photo_path"): 
        return await update.message.reply_text(t(update, context, "send_photo_first"))
    
    await update.message.reply_text(t(update, context, "voice_processing"))
    voice_path = os.path.join(UPLOAD_DIR, f"voice_{update.effective_user.id}.ogg")
    tg_file = await context.bot.get_file(update.message.voice.file_id)
    await tg_file.download_to_drive(voice_path)
    
    try:
        transcription = transcribe_voice(voice_path)
        await update.message.reply_text(f"🎤 {transcription['text']}")
        await process_request(update, context, transcription['text'])
    except Exception as e: 
        print(f"Voice processing error: {e}")
        await update.message.reply_text(t(update, context, "voice_failed"))
    finally:
        # حذف فایل صوتی بعد از استفاده
        if os.path.exists(voice_path):
            os.remove(voice_path)

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("style_"):
        context.user_data["style"] = data.replace("style_", "")
        await query.message.reply_text("☀️🌙 Time?", reply_markup=time_keyboard(update, context))
    elif data.startswith("time_"):
        context.user_data["time_of_day"] = data.replace("time_", "") if "skip" not in data else None
        await query.message.reply_text("🌧❄️ Weather?", reply_markup=weather_keyboard(update, context))
    elif data.startswith("weather_"):
        context.user_data["weather"] = data.replace("weather_", "") if "skip" not in data else None
        context.user_data["awaiting_description"] = True
        await query.message.reply_text(t(update, context, "ask_change"))
    elif data == "redo":
        context.user_data["awaiting_description"] = True
        await query.message.reply_text(t(update, context, "ask_change"))
    elif data == "change_style":
        await query.message.reply_text(t(update, context, "choose_style"), reply_markup=style_keyboard(update, context))
    elif data == "mint_hint":
        try:
            from nft import create_mint_request
            await query.message.reply_text("⏳ Uploading to IPFS...")
            mint_data = create_mint_request(context.user_data["last_project_id"], "Pending", "ArchAgent Design", "AI on TON", context.user_data["last_generated_image"])
            await query.message.reply_text(f"✅ Pinned!\n{mint_data['metadata_url']}\nConnect wallet in TON Panel.")
        except Exception as e: 
            print(f"NFT Minting error: {e}")
            await query.message.reply_text("❌ Error during NFT processing.")

# --- ۵. اجرای سرور و ربات ---

app_web = FastAPI()
@app_web.get("/webapp/index.html")
def webapp():
    return HTMLResponse(content="""<html><body style="background:#1e1e1e;color:white;text-align:center;padding:50px;"><h2>💎 TON Panel</h2><div id="ton-connect"></div><script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script><script>const tc=new TON_CONNECT_UI.TonConnectUI({manifestUrl:'https://raw.githubusercontent.com/ton-community/tutorials/main/03-client/test/public/tonconnect-manifest.json',buttonRootId:'ton-connect'});</script></body></html>""")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # ثبت هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: process_request(u, c, u.message.text) if c.user_data.get("awaiting_description") else None))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    
    # اجرای FastAPI در یک Thread جداگانه
    threading.Thread(target=lambda: uvicorn.run(app_web, host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    
    # اجرای ربات
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__": 
    main()
