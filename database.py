import sqlite3
from datetime import datetime
import hashlib

DB_NAME = "app_data.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def ensure_column_exists(conn, table_name, column_name, column_def):
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in c.fetchall()]
    if column_name not in columns:
        c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        conn.commit()

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password TEXT NOT NULL, name TEXT NOT NULL,
        email TEXT, role TEXT NOT NULL DEFAULT 'user', created_at TEXT,
        question_count INTEGER DEFAULT 0, status TEXT DEFAULT 'فعال'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, 
        question TEXT NOT NULL, created_at TEXT NOT NULL, doc_chars INTEGER DEFAULT 0
    )""")
    ensure_column_exists(conn, "users", "status", "TEXT DEFAULT 'فعال'")
    
    admin_username = "admin"
    c.execute("SELECT username FROM users WHERE username = ?", (admin_username,))
    if not c.fetchone():
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO users (username, password, name, email, role, created_at, status) VALUES (?,?,?,?,?,?,?)",
                  (admin_username, hash_password("123456"), "مدیر سیستم", "admin@site.com", "admin", now, 'فعال'))
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_db()
    c = conn.cursor()
    hashed_password = hash_password(password)
    c.execute("SELECT username, name, email, role, question_count, created_at, status FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    row = c.fetchone()
    conn.close()
    if not row: return False, None
    return True, {"username": row[0], "name": row[1], "email": row[2], "role": row[3], "question_count": row[4], "created_at": row[5], "status": row[6]}

def toggle_user_status(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET status = CASE WHEN status = 'فعال' THEN 'غیرفعال' ELSE 'فعال' END WHERE username = ?", (username,))
    conn.commit()
    c.execute("SELECT status FROM users WHERE username = ?", (username,))
    res = c.fetchone()[0]
    conn.close()
    return res

def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, name, email, role, created_at, question_count, status FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# بقیه توابع شما (add_question, delete_user, get_stats) بدون تغییر باقی بماند
def add_question(username, question, doc_chars=0):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO questions (username, question, created_at, doc_chars) VALUES (?, ?, ?, ?)", (username, question, now, int(doc_chars or 0)))
    c.execute("UPDATE users SET question_count = COALESCE(question_count, 0) + 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def delete_user(username):
    if username == "admin": return False, "حذف ادمین مجاز نیست"
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM questions WHERE username = ?", (username,))
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True, "حذف شد"

def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); u_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM questions"); q_count = c.fetchone()[0]
    conn.close()
    return {"users_count": u_count, "questions_count": q_count}

def get_questions_for_user(username, limit=200):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT question, created_at FROM questions WHERE username = ? ORDER BY created_at DESC LIMIT ?", (username, int(limit)))
    rows = c.fetchall()
    conn.close()
    return rows
def get_today_question_count(username):
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM questions WHERE username = ? AND created_at LIKE ?", (username, f"{today}%"))
    count = c.fetchone()[0]
    conn.close()
    return count
def register_user(username, password, name, email):
    conn = get_db()
    c = conn.cursor()
    try:
        # بررسی تکراری نبودن نام کاربری
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if c.fetchone() is not None:
            return False, "این نام کاربری قبلاً ثبت شده است."

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hashed = hash_password(password)

        c.execute("""
            INSERT INTO users (username, password, name, email, role, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, hashed, name, email, 'user', now, 'فعال'))

        conn.commit()
        return True, "ثبت‌نام با موفقیت انجام شد."
    except Exception as e:
        return False, f"خطا در ذخیره‌سازی اطلاعات: {str(e)}"
    finally:
        conn.close()
