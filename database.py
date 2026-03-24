import sqlite3
import os

DB_PATH = "arch_agent.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # اضافه کردن ستون referred_by برای ردیابی دعوت‌ها
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

def create_user_if_not_exists(user_id, lang='en'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def add_credits(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
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

# تابع حیاتی برای سیستم رفرال
def add_referral(new_user_id, referrer_id):
    if str(new_user_id) == str(referrer_id): return False
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT referred_by FROM users WHERE user_id = ?", (new_user_id,))
    row = c.fetchone()
    
    # اگر کاربر قبلاً وجود نداشته یا رفرال نداشته
    if row is None or row[0] is None:
        # ثبت معرف
        c.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, new_user_id))
        # جایزه ۱۰ کریدیت به معرف (چون سخاوتمندانه است!)
        c.execute("UPDATE users SET credits = credits + 10 WHERE user_id = ?", (referrer_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False
