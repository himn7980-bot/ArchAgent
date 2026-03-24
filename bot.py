import os
import asyncio
import threading
import json
from PIL import Image

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

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
import database

# راه‌اندازی دیتابیس
database.init_db()

# راه‌اندازی کلاینت OpenAI
openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# =========================
# Language & Helpers
# =========================

def detect_message_lang(text: str) -> str:
    if not text: return "en"
    if any(ch in text for ch in "پچژگکی"): return "fa"
    if any(ch in text for ch in "ةؤإأيي"): return "ar"
    if any("\u0400" <= ch <= "\u04FF" for ch in text): return "ru"
    return "en"

def get_user_lang(update: Update):
    user_id = update.effective_user.id
    db_user = database.get_user(user_id)
    if db_user: return db_user["lang"]
    lang = (update.effective_user.language_code or "en").lower()
    if lang.startswith("fa"): return "fa"
    if lang.startswith("ar"): return "ar"
    if lang.startswith("ru"): return "ru"
    return "en"

def t(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    lang = get_user_lang(update)
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)

def reset_user_flow(context):
    lang = context.user_data.get("lang")
    context.user_data.clear()
    if lang: context.user_data["lang"] = lang

def get_upsell_keyboard(update, context):
    btn_text = t(update, context, "premium_btn")
    return InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, web_app=WebAppInfo(url=f"{MINIAPP_URL}?user_id={update.effective_user.id}"))]])

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

def result_keyboard(update, context, project_id):
    btn_text = t(update, context, "ton_panel_btn")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Regenerate", callback_data="redo"), InlineKeyboardButton("🎨 Change Style", callback_data="change_style")],
        [InlineKeyboardButton(btn_text, web_app=WebAppInfo(url=f"{MINIAPP_URL}?user_id={update.effective_user.id}")), InlineKeyboardButton("🖼 Mint NFT", callback_data="mint_hint")],
    ])

# =========================
# Core AI Process (Image)
# =========================

async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_id = update.effective_user.id
    db_user = database.get_user(user_id)
    
    if not db_user or db_user["credits"] < 10:
        return await update.message.reply_text(t(update, context, "upsell"), reply_markup=get_upsell_keyboard(update, context), parse_mode="Markdown")

    data = context.user_data
    if not data.get("photo_path") or not os.path.exists(data["photo_path"]):
        return await update.message.reply_text("⚠️ Please send a photo first.")

    database.deduct_credit(user_id, amount=10)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text(t(update, context, "generating"))

    try:
        english_request = translate_request_to_english(user_text)
        prompt_data = PromptEngine.build_final_prompt(
            space_type=data.get("space_type", "interior"),
            style=data.get("style", "modern"),
            time_of_day=data.get("time_of_day"),
            weather=data.get("weather"),
            user_text=english_request,
        )

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
        generated = generate_design(data["photo_path"], None, prompt_data)

        project_id = create_project(str(user_id), {"generated_image": generated, "prompt": str(prompt_data)})

        if generated.startswith("http"):
            await update.message.reply_photo(generated)
        else:
            with open(generated, "rb") as img:
                await update.message.reply_photo(img)

        if db_user["is_premium"]:
            stores = get_store_suggestions(data["space_type"], data["style"])
            if stores: await update.message.reply_text(f"🛒 **Stores & Materials:**\n" + "\n".join(stores), parse_mode="Markdown")
            cost = estimate_cost(data["space_type"], data["style"])
            if cost: await update.message.reply_text(f"📊 **Cost Estimation:**\n{str(cost)}", parse_mode="Markdown")
        else:
            materials = suggest_materials(data["space_type"], data["style"])
            if materials: await update.message.reply_text("\n".join(materials))

        context.user_data.update({"awaiting_description": False, "last_project_id": project_id, "last_generated_image": generated, "last_request_text": user_text})
        await update.message.reply_text(t(update, context, "wallet_prompt"), reply_markup=result_keyboard(update, context, project_id))

    except Exception as e:
        print(f"Error: {e}")
        database.add_credits(user_id, 10) 
        await update.message.reply_text(f"❌ Error: {str(e)}")

# =========================
# Handlers
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(update)
    
    # مدیریت رفرال
    is_new = database.create_user_if_not_exists(user_id, lang)
    if is_new and context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if database.add_referral(user_id, referrer_id):
            try:
                # اطلاع‌رسانی به معرف به زبان خودش
                ref_user = database.get_user(referrer_id)
                ref_lang = ref_user["lang"] if ref_user else "en"
                await context.bot.send_message(
                    chat_id=referrer_id, 
                    text=TEXTS.get(ref_lang, TEXTS["en"])["referral_success"]
                )
            except: pass

    reset_user_flow(context)
    
    # ساخت لینک اختصاصی رفرال
    bot_obj = await context.bot.get_me()
    invite_link = f"https://t.me/{bot_obj.username}?start={user_id}"
    
    # دکمه‌ها
    lang_data = TEXTS.get(lang, TEXTS["en"])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(lang_data["ton_panel_btn"], web_app=WebAppInfo(url=f"{MINIAPP_URL}?user_id={user_id}"))],
        [InlineKeyboardButton(lang_data["invite_btn"], switch_inline_query=f"\n{lang_data['share_msg']}\n{invite_link}")]
    ])
    
    await update.message.reply_text(lang_data["welcome"], reply_markup=keyboard, parse_mode="Markdown")

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_user = database.get_user(user_id)
    if not db_user: return await update.message.reply_text("User not found.")

    is_premium, credits = db_user["is_premium"], db_user["credits"]
    icon = "💎" if is_premium else ""
    status = "Premium Member" if is_premium else "Free User"
    
    text = t(update, context, "profile").format(name=update.effective_user.first_name, icon=icon, status=status, credits=credits)
    await update.message.reply_text(text, reply_markup=get_upsell_keyboard(update, context), parse_mode="Markdown")

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # این بخش برای امنیت بیشتر و هماهنگی با API جدید نگه داشته شده است
    pass

def process_image_sync(temp_path: str, image_path: str):
    with Image.open(temp_path) as img:
        img = img.convert("RGBA")
        scale = min(1024 / img.size[0], 1024 / img.size[1])
        new = (int(img.size[0] * scale), int(img.size[1] * scale))
        resized = img.resize(new, Image.LANCZOS)
        canvas = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        canvas.paste(resized, ((1024 - new[0]) // 2, (1024 - new[1]) // 2))
        canvas.save(image_path)
    if os.path.exists(temp_path): os.remove(temp_path)

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)

    photo_file = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo_file.file_id)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    image_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}.png")
    temp = image_path + ".temp"

    await tg_file.download_to_drive(temp)
    await asyncio.to_thread(process_image_sync, temp, image_path)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try: scene = detect_scene(image_path)
    except: scene = "interior"

    context.user_data.update({
        "photo_path": image_path, "space_type": scene, "style": None, "time_of_day": None, "weather": None, "awaiting_description": False,
    })
    await update.message.reply_text(f"Scene detected: {scene}\nChoose style:", reply_markup=style_keyboard())

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    lang = detect_message_lang(text)
    database.update_user_lang(user_id, lang)

    if context.user_data.get("awaiting_description"):
        if not context.user_data.get("photo_path") or not os.path.exists(context.user_data["photo_path"]):
            return await update.message.reply_text("⚠️ لطفا ابتدا یک عکس از فضا ارسال کنید.")
        await process_request(update, context, text)
    else:
        db_user = database.get_user(user_id)
        if not db_user or db_user["credits"] < 1:
            return await update.message.reply_text(t(update, context, "upsell"), reply_markup=get_upsell_keyboard(update, context), parse_mode="Markdown")

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        system_prompt = (
            "You are ArchAgent, an expert AI architect. "
            "If the user asks for advice, reply normally in their language. "
            "HOWEVER, if the user explicitly asks you to 'design', 'create', 'draw', or 'generate' an image/scene from scratch, "
            "ONLY reply with EXACTLY this format: [GENERATE] <highly detailed architectural prompt in English>"
        )
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            )
            ai_reply = response.choices[0].message.content.strip()

            if ai_reply.startswith("[GENERATE]"):
                if db_user["credits"] < 10:
                    return await update.message.reply_text(t(update, context, "upsell"), reply_markup=get_upsell_keyboard(update, context), parse_mode="Markdown")
                
                image_prompt = ai_reply.replace("[GENERATE]", "").strip()
                database.deduct_credit(user_id, amount=10)
                
                await update.message.reply_text("✨ دستیار در حال خلق ایده ذهنی شماست...")
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
                
                final_prompt = {"prompt": f"{image_prompt}, architectural photography, 8k resolution, photorealistic", "negative_prompt": "cartoon, illustration, low quality, distorted"}
                generated = generate_design(None, None, final_prompt)
                
                if generated.startswith("http"):
                    await update.message.reply_photo(generated, caption="🎨 طرح پیشنهادی دستیار")
                else:
                    with open(generated, "rb") as img:
                        await update.message.reply_photo(img, caption="🎨 طرح پیشنهادی دستیار")
            else:
                database.deduct_credit(user_id, amount=1)
                await update.message.reply_text(ai_reply)

        except Exception as e:
            print(f"OpenAI Error: {e}")
            await update.message.reply_text("❌ خطا در ارتباط با دستیار هوشمند.")

async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("photo_path") or not os.path.exists(context.user_data["photo_path"]):
        return await update.message.reply_text("⚠️ Please send a photo first.")
    path = os.path.join(UPLOAD_DIR, f"voice_{update.effective_user.id}.ogg")
    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        await file.download_to_drive(path)
        transcription = transcribe_voice(path)
        text = transcription.get("text", "")
        if not text: return await update.message.reply_text("Could not understand the voice.")
        await update.message.reply_text(f"🎤 You said: {text}")
        context.user_data["awaiting_description"] = True
        await process_request(update, context, text)
    except Exception as e:
        pass
    finally:
        if os.path.exists(path): os.remove(path)

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

# =========================
# FastAPI & WebApp (TON Payment)
# =========================

app_web = FastAPI()

app_web.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MY_WALLET_ADDRESS = "UQDPVUpClyvBg0GXnl-IHVB6Q5I_CRp-psFhkasI-uPMpUfm"

@app_web.get("/")
@app_web.get("/ping")
def health(): return {"ArchAgent": "running", "status": "200 OK"}

# مسیر جدید برای تایید پرداخت و شارژ آنی دیتابیس
@app_web.get("/confirm_payment")
async def confirm_payment(user_id: int, package: str):
    added = {"starter": 150, "pro": 400, "master": 1000}.get(package, 0)
    database.add_credits(user_id, added)
    return {"status": "success", "added": added}

@app_web.get("/tonconnect-manifest.json")
def get_manifest(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return JSONResponse({
        "url": base_url,
        "name": "ArchAgent Store",
        "iconUrl": "https://cdn-icons-png.flaticon.com/512/2830/2830305.png"
    })

@app_web.get("/webapp/index.html")
def webapp():
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ArchAgent Store</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
        <style>
            body {{ font-family: sans-serif; background-color: #181818; color: white; text-align: center; padding: 20px; margin: 0; }}
            .container {{ max-width: 400px; margin: auto; }}
            .package-card {{ background: #222; border: 1px solid #333; border-radius: 12px; padding: 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
            .package-info {{ text-align: left; }}
            .package-title {{ font-size: 18px; font-weight: bold; color: #0098EA; margin-bottom: 5px; }}
            .package-desc {{ font-size: 13px; color: #aaa; }}
            .buy-btn {{ background: #0098EA; color: white; border: none; padding: 10px 15px; border-radius: 8px; font-weight: bold; cursor: pointer; display: none; }}
            #ton-connect {{ display: flex; justify-content: center; margin-bottom: 25px; }}
            .header-text {{ margin-bottom: 20px; font-size: 14px; color: #ddd; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>💎 Buy Credits</h2>
            <p class="header-text">1 Image = 10 Credits | 1 Chat = 1 Credit</p>
            <div id="ton-connect"></div>
            
            <div class="package-card">
                <div class="package-info">
                    <div class="package-title">Starter Pack</div>
                    <div class="package-desc">150 Credits</div>
                </div>
                <button class="buy-btn" onclick="buyPackage('starter', '0.5')">0.5 TON</button>
            </div>

            <div class="package-card" style="border-color: #0098EA;">
                <div class="package-info">
                    <div class="package-title">Pro Pack 🔥</div>
                    <div class="package-desc">400 Credits (Best Value)</div>
                </div>
                <button class="buy-btn" onclick="buyPackage('pro', '1.0')">1 TON</button>
            </div>

            <div class="package-card">
                <div class="package-info">
                    <div class="package-title">Master Pack</div>
                    <div class="package-desc">1000 Credits</div>
                </div>
                <button class="buy-btn" onclick="buyPackage('master', '2.0')">2 TON</button>
            </div>
            <p id="status-msg" style="margin-top: 15px; color: #4CAF50;"></p>
        </div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const manifestUrl = window.location.origin + '/tonconnect-manifest.json';
            
            const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
                manifestUrl: manifestUrl,
                buttonRootId: 'ton-connect'
            }});

            tonConnectUI.onStatusChange(wallet => {{
                const buttons = document.querySelectorAll('.buy-btn');
                buttons.forEach(btn => btn.style.display = wallet ? 'block' : 'none');
            }});

            async function buyPackage(pkgType, priceTon) {{
                try {{
                    const nanoTon = Math.floor(parseFloat(priceTon) * 1000000000);
                    
                    const transaction = {{
                        validUntil: Math.floor(Date.now() / 1000) + 360,
                        messages: [{{
                            address: "{MY_WALLET_ADDRESS}",
                            amount: nanoTon.toString()
                        }}]
                    }};

                    document.getElementById('status-msg').style.color = "#4CAF50";
                    document.getElementById('status-msg').innerText = "⏳ Confirm transaction in your wallet...";
                    
                    await tonConnectUI.sendTransaction(transaction);
                    
                    // فراخوانی مستقیم API شارژ برای حل مشکل شارژ نشدن اعتبار
                    const uid = new URLSearchParams(window.location.search).get('user_id');
                    document.getElementById('status-msg').innerText = "⌛ Charging credits...";
                    await fetch('/confirm_payment?user_id=' + uid + '&package=' + pkgType);

                    document.getElementById('status-msg').innerText = "✅ Success! Returning to bot...";
                    setTimeout(() => {{ tg.close(); }}, 1500);
                    
                }} catch (e) {{
                    alert("⚠️ Error Details: " + e.message); 
                    document.getElementById('status-msg').style.color = "#FF5252";
                    document.getElementById('status-msg').innerText = "❌ Payment failed or cancelled.";
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# =========================
# Main Setup
# =========================

def run_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("me", show_profile))
    app.add_handler(CommandHandler("profile", show_profile))
    
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    print("🚀 ArchAgent bot is polling with Unified Coin System...")
    app.run_polling(stop_signals=None)

def main():
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Starting Web Server on port {port} for Render/UptimeRobot...")
    uvicorn.run(app_web, host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    main()
