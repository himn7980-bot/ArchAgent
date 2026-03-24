import sqlite3
import os

DB_PATH = "archagent.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # اضافه شدن ستون referred_by برای سیستم دعوت از دوستان
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            credits INTEGER DEFAULT 30,
            is_premium INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'en',
            referred_by INTEGER DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT credits, is_premium, lang, referred_by FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"credits": row[0], "is_premium": bool(row[1]), "lang": row[2], "referred_by": row[3]}
    return None

def create_user_if_not_exists(user_id, lang="en"):
    if not get_user(user_id):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, credits, is_premium, lang) VALUES (?, 30, 0, ?)", (user_id, lang))
        conn.commit()
        conn.close()
        return True
    return False

def add_referral(new_user_id, referrer_id):
    if str(new_user_id) == str(referrer_id): return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # ثبت معرف و جایزه ۱۰ کریدیتی به دعوت‌کننده
    c.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, new_user_id))
    c.execute("UPDATE users SET credits = credits + 10 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    conn.close()
    return True

def add_credits(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ?, is_premium = 1 WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def deduct_credit(user_id, amount=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = MAX(0, credits - ?) WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_user_lang(user_id, lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()
