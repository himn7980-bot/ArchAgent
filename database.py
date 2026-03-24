import sqlite3
import os

# دیتابیس دقیقاً کنار فایل‌های پروژه ساخته می‌شود (عالی برای تست و هکاتون)
DB_PATH = "archagent.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            credits INTEGER DEFAULT 3,
            is_premium INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'en'
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT credits, is_premium, lang FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"credits": row[0], "is_premium": bool(row[1]), "lang": row[2]}
    return None

def create_user_if_not_exists(user_id, lang="en"):
    if not get_user(user_id):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, credits, is_premium, lang) VALUES (?, 3, 0, ?)", (user_id, lang))
        conn.commit()
        conn.close()

def update_user_lang(user_id, lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def add_credits(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # با خرید بسته، هم کریدیت اضافه می‌شود و هم کاربر Premium می‌شود
    c.execute("UPDATE users SET credits = credits + ?, is_premium = 1 WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def deduct_credit(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - 1 WHERE user_id = ? AND credits > 0", (user_id,))
    conn.commit()
    conn.close()
