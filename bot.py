import os
import threading
from PIL import Image, ImageDraw

import uvicorn
from fastapi import FastAPI
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

    has_persian_specific = False
    has_arabic_block = False

    for ch in text:
        if "\u0600" <= ch <= "\u06FF":
            has_arabic_block = True
            if ch in "پچژگک":
                has_persian_specific = True

        if "\u0400" <= ch <= "\u04FF":
            return "ru"

    if has_persian_specific:
        return "fa"
    if has_arabic_block:
        return "ar"
    return "en"


def get_user_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    saved_lang = context.user_data.get("lang")
    if saved_lang:
        return saved_lang

    lang = (update.effective_user.language_code or "en").lower()

    if lang.startswith("fa"):
        return "fa"
    if lang.startswith("ar"):
        return "ar"
    if lang.startswith("ru"):
        return "ru"
    return "en"


def t(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> str:
    lang = get_user_lang(update, context)
    return TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))


def style_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)

    labels = {
        "en": {
            "modern": "🟦 Modern",
            "classic": "🏛 Classic",
            "minimal": "⚪ Minimal",
            "luxury": "✨ Luxury",
            "arabic": "🕌 Arabic",
        },
        "fa": {
            "modern": "🟦 مدرن",
            "classic": "🏛 کلاسیک",
            "minimal": "⚪ مینیمال",
            "luxury": "✨ لوکس",
            "arabic": "🕌 عربی",
        },
        "ar": {
            "modern": "🟦 حديث",
            "classic": "🏛 كلاسيكي",
            "minimal": "⚪ مينيمال",
            "luxury": "✨ فاخر",
            "arabic": "🕌 عربي",
        },
        "ru": {
            "modern": "🟦 Современный",
            "classic": "🏛 Классический",
            "minimal": "⚪ Минимализм",
            "luxury": "✨ Люкс",
            "arabic": "🕌 Арабский",
        },
    }

    l = labels.get(lang, labels["en"])

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(l["modern"], callback_data="style_modern"),
                InlineKeyboardButton(l["classic"], callback_data="style_classic"),
            ],
            [
                InlineKeyboardButton(l["minimal"], callback_data="style_minimal"),
                InlineKeyboardButton(l["luxury"], callback_data="style_luxury"),
            ],
            [
                InlineKeyboardButton(l["arabic"], callback_data="style_arabic"),
            ],
        ]
    )


def result_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str) -> InlineKeyboardMarkup:
    lang = get_user_lang(update, context)

    labels = {
        "en": {
            "redo": "🔁 Regenerate",
            "style": "🎨 Change Style",
            "pay": "💰 TON Panel",
            "mint": "🖼 Mint NFT",
        },
        "fa": {
            "redo": "🔁 تغییر طرح",
            "style": "🎨 تغییر سبک",
            "pay": "💰 پنل TON",
            "mint": "🖼 مینت NFT",
        },
        "ar": {
            "redo": "🔁 إعادة التصميم",
            "style": "🎨 تغيير النمط",
            "pay": "💰 لوحة TON",
            "mint": "🖼 سك NFT",
        },
        "ru": {
            "redo": "🔁 Новый вариант",
            "style": "🎨 Сменить стиль",
            "pay": "💰 TON панель",
            "mint": "🖼 Создать NFT",
        },
    }

    l = labels.get(lang, labels["en"])

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(l["redo"], callback_data="redo"),
                InlineKeyboardButton(l["style"], callback_data="change_style"),
            ],
            [
                InlineKeyboardButton(
                    l["pay"],
                    web_app=WebAppInfo(
                        url=f"{MINIAPP_URL}?project_id={project_id}&user_id={update.effective_user.id}"
                    ),
                ),
                InlineKeyboardButton(l["mint"], callback_data="mint_hint"),
            ],
        ]
    )


def build_prompt(space_type: str, style: str, user_text: str) -> str:
    style_text = {
        "modern": "modern architectural style",
        "classic": "classical architectural style",
        "minimal": "minimal clean contemporary style",
        "luxury": "luxury premium style",
        "arabic": "Middle Eastern / Arabic elegant style",
    }.get(style, "professional design style")

    common_rules = f"""
User request:
{user_text}

Style direction:
{style_text}

Rules:
- Keep the original structure and proportions
- Keep the same camera angle
- Do not add text, letters, signage, writing, posters or banners
- Keep the result realistic and buildable
- Professional architectural visualization
- High quality realistic render
""".strip()

    if space_type == "interior":
        return f"""
Redesign this exact interior space.

{common_rules}

Extra interior rules:
- Keep the same room layout
- Do not change the structure of the room
- Only redesign materials, furniture, decoration and lighting
- Keep surfaces clean and architectural
""".strip()

    if space_type == "exterior":
        return f"""
Architectural facade redesign based on the provided building photo.

{common_rules}

Extra exterior rules:
- Keep the exact same building structure
- Preserve the number of floors
- Maintain the same window layout
- Only redesign facade style, materials and decorative elements
""".strip()

    if space_type == "unfinished":
        return f"""
Redesign this unfinished architectural or interior space into a completed realistic design.

{common_rules}

Extra unfinished rules:
- Preserve the original structure and proportions
- Complete unfinished surfaces and details
- Add realistic finishing materials
- Keep the same space composition
""".strip()

    return f"""
Renovate this existing old space or building based on the user's request.

{common_rules}

Extra renovation rules:
- Preserve the original layout and proportions
- Improve the style, materials and overall appearance
- Make it look realistically renovated
""".strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["lang"] = get_user_lang(update, context)
    context.user_data["awaiting_description"] = False
    await update.message.reply_text(t(update, context, "welcome"))


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return

    photo_file = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo_file.file_id)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    temp_jpg_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}.jpg")
    image_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}.png")
    mask_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}_mask.png")

    await tg_file.download_to_drive(temp_jpg_path)

    # 1. Anti-Stretch: Letterboxing the image onto a 1024x1024 canvas
    target_size = 1024
    with Image.open(temp_jpg_path) as img:
        img = img.convert("RGBA")
        original_width, original_height = img.size

        scale = min(target_size / original_width, target_size / original_height)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        resized = img.resize((new_width, new_height), Image.LANCZOS)

        canvas = Image.new("RGBA", (target_size, target_size), (255, 255, 255, 255))
        paste_x = (target_size - new_width) // 2
        paste_y = (target_size - new_height) // 2
        canvas.paste(resized, (paste_x, paste_y), resized)
        canvas.save(image_path, "PNG")

    # 2. Creating Mask for Inpainting
    mask_canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(mask_canvas)
    margin = 50 # Preserving context around the edges
    draw.rectangle([margin, margin, target_size - margin, target_size - margin], fill=(0, 0, 0, 0))
    mask_canvas.save(mask_path, "PNG")

    context.user_data["photo_path"] = image_path
    context.user_data["mask_path"] = mask_path
    context.user_data["space_type"] = "interior"
    context.user_data["style"] = None
    context.user_data["awaiting_description"] = False

    await update.message.reply_text(t(update, context, "photo_received"))

    try:
        detected_scene = detect_scene(image_path)
    except Exception:
        detected_scene = "interior"

    context.user_data["space_type"] = detected_scene

    await update.message.reply_text(
        f"{t(update, context, 'scene_detected')} {detected_scene}"
    )
    await update.message.reply_text(
        t(update, context, "choose_style"),
        reply_markup=style_keyboard(update, context),
    )


async def handle_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    mapping = {
        "style_modern": "modern",
        "style_classic": "classic",
        "style_minimal": "minimal",
        "style_luxury": "luxury",
        "style_arabic": "arabic",
    }

    selected_style = mapping.get(query.data)

    if not selected_style:
        await query.message.reply_text("Style not found.")
        return

    context.user_data["style"] = selected_style
    context.user_data["awaiting_description"] = True

    await query.message.reply_text(t(update, context, "ask_change"))


async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> None:
    photo_path = context.user_data.get("photo_path")
    mask_path = context.user_data.get("mask_path")
    style = context.user_data.get("style")
    awaiting_description = context.user_data.get("awaiting_description", False)

    if not photo_path or not os.path.exists(photo_path):
        await update.message.reply_text(t(update, context, "send_photo_first"))
        return

    if not style:
        await update.message.reply_text(t(update, context, "choose_style_first"))
        return

    if not awaiting_description:
        await update.message.reply_text(t(update, context, "ask_change"))
        return

    space_type = context.user_data.get("space_type", "interior")

    await update.message.reply_text(t(update, context, "generating"))

    try:
        prompt = build_prompt(space_type, style, user_text)
        generated_image = generate_design(photo_path, mask_path, prompt)

        project_payload = {
            "space_type": space_type,
            "style": style,
            "request_text": user_text,
            "source_image": photo_path,
            "generated_image": generated_image,
        }
        project_id = create_project(str(update.effective_user.id), project_payload)

        if isinstance(generated_image, str) and generated_image.startswith("http"):
            await update.message.reply_photo(
                photo=generated_image,
                caption=t(update, context, "result_caption"),
            )
        else:
            with open(generated_image, "rb") as img_file:
                await update.message.reply_photo(
                    photo=img_file,
                    caption=t(update, context, "result_caption"),
                )

        await update.message.reply_text(
            t(update, context, "materials_title")
            + "\n- "
            + "\n- ".join(suggest_materials(space_type, style))
        )

        await update.message.reply_text(
            t(update, context, "cost_title") + f"\n{estimate_cost(space_type, style)}"
        )

        await update.message.reply_text(
            t(update, context, "stores_title")
            + "\n- "
            + "\n- ".join(get_store_suggestions(space_type, style))
        )

        await update.message.reply_text(
            t(update, context, "wallet_prompt"),
            reply_markup=result_keyboard(update, context, project_id),
        )

        context.user_data["awaiting_description"] = False

    except Exception as e:
        await update.message.reply_text(t(update, context, "ai_failed"))
        await update.message.reply_text(str(e))


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    context.user_data["lang"] = detect_message_lang(user_text)
    await process_request(update, context, user_text)


async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return

    if "photo_path" not in context.user_data:
        await update.message.reply_text(t(update, context, "send_photo_first"))
        return

    if not context.user_data.get("style"):
        await update.message.reply_text(t(update, context, "choose_style_first"))
        return

    await update.message.reply_text(t(update, context, "voice_processing"))

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    voice_path = os.path.join(UPLOAD_DIR, f"{update.effective_user.id}_voice.ogg")

    voice = update.message.voice
    tg_file = await context.bot.get_file(voice.file_id)
    await tg_file.download_to_drive(voice_path)

    try:
        transcribed_text = transcribe_voice(voice_path)
        context.user_data["lang"] = detect_message_lang(transcribed_text)
        context.user_data["awaiting_description"] = True

        await update.message.reply_text(transcribed_text)
        await process_request(update, context, transcribed_text)

    except Exception as e:
        await update.message.reply_text(t(update, context, "voice_failed"))
        await update.message.reply_text(str(e))


async def handle_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    data = query.data

    if data == "redo":
        context.user_data["awaiting_description"] = True
        await query.message.reply_text(t(update, context, "ask_change"))

    elif data == "change_style":
        context.user_data["awaiting_description"] = False
        context.user_data["style"] = None
        await query.message.reply_text(
            t(update, context, "choose_style"),
            reply_markup=style_keyboard(update, context),
        )

    elif data == "mint_hint":
        await query.message.reply_text(t(update, context, "coming_mint"))


app_web = FastAPI()


@app_web.get("/")
def health():
    return {"app": "ArchAgent", "ok": True}


def run_api() -> None:
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app_web, host="0.0.0.0", port=port)


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(CallbackQueryHandler(handle_style, pattern="^style_"))
    app.add_handler(
        CallbackQueryHandler(handle_actions, pattern="^(redo|change_style|mint_hint)$")
    )
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, description))

    print("ArchAgent running...")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    threading.Thread(target=run_api, daemon=True).start()
    main()
