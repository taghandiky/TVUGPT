import streamlit as st
import pandas as pd
import database as db
import datetime
from utils.pdf_handler import extract_text_from_pdfs
from utils.ai_engine import generate_chat_response, extract_important_sentences
from utils.ai_engine import test_api_key

# چک کردن کلید API
if not test_api_key():
    st.error("❌ اتصال به سرویس هوش مصنوعی برقرار نشد یا API Key معتبر نیست.")
    st.stop()

# --- تنظیمات سیستمی ---
MAX_QUESTIONS_PER_DAY = 20

st.set_page_config(page_title="سامانه هوشمند دانشگاه ملی مهارت", page_icon="💎", layout="wide")
db.init_db()

# --- CSS کامل و فوق حرفه‌ای ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Vazirmatn', sans-serif !important; direction: rtl; text-align: right; }
    .stApp { background: #0f172a; color: #e2e8f0; }
    .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important; }
    
    /* نوار بالا */
    .top-bar {
        background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 15px;
        padding: 15px 25px; margin-bottom: 25px;
        display: flex; justify-content: space-between; align-items: center; direction: rtl;
    }
    .user-profile-section { display: flex; align-items: center; gap: 12px; margin-left: auto; direction: rtl; }

    /* کانتینر اصلی چت و ابزارها */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.01) !important;
        border: 1px solid rgba(59, 130, 246, 0.15) !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), inset 0 0 20px rgba(59, 130, 246, 0.05) !important;
        backdrop-filter: blur(5px);
    }

    /* بنر خوش‌آمدگویی شیشه‌ای جدید */
    .welcome-card {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(30, 41, 59, 0.7) 100%);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 25px;
        padding: 30px;
        margin: 15px 0 30px 0;
        text-align: center;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        position: relative;
        overflow: hidden;
    }
    .status-badge {
        background: rgba(34, 197, 94, 0.1);
        color: #4ade80;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 15px;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }
    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #22c55e;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); }
        100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }
    .welcome-title { color: #f8fafc; font-size: 22px; font-weight: 700; margin-bottom: 8px; }
    .welcome-subtitle { color: #94a3b8; font-size: 15px; line-height: 1.7; max-width: 90%; margin: 0 auto; }

    /* استایل‌های پیام‌ها */
    .stChatMessage { background: rgba(255,255,255,0.04) !important; border-radius: 15px !important; margin-bottom: 10px !important; }
    .stButton>button { border-radius: 10px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 0.5rem 1rem; }
    
    .custom-card { 
        background: rgba(255, 255, 255, 0.03); 
        border: 1px solid rgba(59, 130, 246, 0.2); 
        border-radius: 20px; 
        padding: 30px 10px; 
        text-align: center; 
        margin-bottom: 15px; 
    }
    .card-title { color: #94a3b8; font-size: 14px; margin-bottom: 10px; }
    .card-value { color: white; font-size: 32px; font-weight: bold; }
    .card-value-small { color: #3b82f6; font-size: 24px; font-weight: bold; }

    .login-title { text-align: center; color: #3b82f6; font-size: 28px; font-weight: bold; text-shadow: 0 0 15px rgba(59, 130, 246, 0.5); margin-bottom: 30px; }
</style>
""", unsafe_allow_html=True)

def logout():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# --- احراز هویت ---
if "authentication_status" not in st.session_state:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="login-title">سامانه هوشمند پاسخگویی<br><span style="color:white; font-size:22px;">دانشگاه ملی مهارت</span></div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["ورود به سیستم", "عضویت جدید"])
        with t1:
            u = st.text_input("نام کاربری")
            p = st.text_input("رمز عبور", type="password")
            if st.button("ورود به پنل پژوهشی", use_container_width=True):
                ok, res = db.verify_user(u, p)
                if ok: st.session_state.authentication_status=True; st.session_state.user=res; st.rerun()
                else: st.error("دسترسی غیرمجاز")
        with t2:
            nu = st.text_input("شناسه کاربری")
            np = st.text_input("کلمه عبور", type="password")
            if st.button("تایید و ساخت حساب", use_container_width=True):
                ok, msg = db.register_user(nu, np, nu, f"{nu}@nus.ac.ir")
                if ok: st.success(msg)
                else: st.error(msg)

# --- داشبورد اصلی ---
else:
    user = st.session_state.user
    is_admin = user['role'] == 'admin'
    is_disabled = user.get('status') == 'غیرفعال'
    
    today_count = db.get_today_question_count(user['username'])

    if is_admin:
        status_label = "وضعیت: نامحدود"
        sub_msg = "مدیر سیستم"
    else:
        status_label = f"محدودیت: {today_count} از ۲۰ پیام"
        sub_msg = "خوش آمدید به دستیار هوشمند دانشگاه"

    st.markdown(f"""
    <div class="top-bar">
        <div class="user-profile-section">
            <span style="font-size: 26px;">💎</span>
            <div style="text-align: right;">
                <strong style="font-size: 18px; display: block; line-height: 1.2;">{user['name']}</strong>
                <small style="color: {'#ef4444' if is_disabled else '#94a3b8'};">
                    {('حساب شما غیرفعال است' if is_disabled else sub_msg)}
                </small>
            </div>
        </div>
        <div style="background: rgba(59, 130, 246, 0.1); padding: 6px 18px; border-radius: 20px; border: 1px solid rgba(59, 130, 246, 0.3);">
            <small style="color: #60a5fa; font-weight: bold; font-size: 14px;">{status_label}</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, _, exit_col = st.columns([4, 1, 0.8])
    if exit_col.button("خروج از حساب", use_container_width=True): logout()

    col_chat, col_tools = st.columns([1.3, 1], gap="medium")

    with col_chat:
        st.markdown("<h5 style='text-align: right;'>💬 دستیار هوشمند پژوهش</h5>", unsafe_allow_html=True)
        
        if is_disabled and not is_admin:
            st.error("🚫 دسترسی شما توسط مدیریت مسدود شده است.")
        elif not is_admin and today_count >= MAX_QUESTIONS_PER_DAY:
            st.warning("⚠️ سقف ۲۰ پیام روزانه شما به پایان رسیده است.")
        else:
            chat_container = st.container(height=580)
            if "messages" not in st.session_state: st.session_state.messages = []
            
            with chat_container:
                # --- بنر خوش‌آمدگویی ارتقا یافته ---
                st.markdown("""
                <div class="welcome-card">
                    <div class="status-badge">
                        <div class="pulse-dot"></div>
                        دستیار آنلاین آماده پاسخگویی
                    </div>
                    <div class="welcome-title">سلام! من دستیار هوشمند دانشگاه هستم</div>
                    <div class="welcome-subtitle">
                        هر سوالی درباره قوانین آموزشی، امتحانات، چارت یا آیین‌نامه‌ها داری، بپرس تا در کسری از ثانیه جواب مستند بهت بدم.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for m in st.session_state.messages:
                    with st.chat_message(m["role"]): st.markdown(m["content"])

            if prompt := st.chat_input("سوال خود را اینجا بپرسید..."):
                if not st.session_state.get("pdf_text"): st.error("❌ ابتدا فایل PDF بارگذاری کنید.")
                else:
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with chat_container:
                        with st.chat_message("user"): st.markdown(prompt)
                        with st.chat_message("assistant"):
                            response = generate_chat_response(st.session_state.messages, st.session_state.pdf_text)
                            st.markdown(response)
                            db.add_question(user['username'], prompt, len(st.session_state.pdf_text))
                            st.session_state.messages.append({"role": "assistant", "content": response})
                            st.rerun()

    with col_tools:
        if is_admin:
            tabs = st.tabs(["📂 مدیریت محتوا", "👥 مدیریت کاربران", "📊 وضعیت سیستم"])
            with tabs[0]:
                admin_files = st.file_uploader("بارگذاری اسناد مرجع (PDF)", type="pdf", accept_multiple_files=True, key="admin_up")
                if st.button("🔍 تحلیل و استخراج نکات", use_container_width=True):
                    if admin_files:
                        with st.spinner("در حال تحلیل محتوا..."):
                            txt, _ = extract_text_from_pdfs(admin_files)
                            st.session_state.pdf_text = txt
                            key_points = extract_important_sentences(txt)
                            st.success("سند با موفقیت تحلیل شد.")
                            st.markdown("### 📌 نکات کلیدی استخراج شده:")
                            for point in key_points: st.markdown(f"- {point}")
                    else: st.error("لطفاً ابتدا فایلی را انتخاب کنید.")
            
            with tabs[1]:
                users_raw = db.get_all_users()
                df = pd.DataFrame(users_raw, columns=['یوزر', 'نام', 'ایمیل', 'نقش', 'تاریخ', 'سوالات', 'وضعیت'])
                st.dataframe(df, use_container_width=True, height=200)
                st.markdown("---")
                selected_user = st.selectbox("انتخاب کاربر:", df['یوزر'].tolist())
                c1, c2 = st.columns(2)
                if c1.button("🔒 فعال/غیرفعال‌سازی", use_container_width=True):
                    new_status = db.toggle_user_status(selected_user)
                    st.toast(f"وضعیت {selected_user} به {new_status} تغییر یافت", icon="✅")
                    st.rerun()
                if c2.button("🗑️ حذف دائمی", use_container_width=True):
                    db.delete_user(selected_user)
                    st.toast(f"کاربر {selected_user} حذف شد")
                    st.rerun()
            
            with tabs[2]:
                stats = db.get_stats()
                sc1, sc2 = st.columns(2)
                with sc1: st.markdown(f'<div class="custom-card"><div class="card-title">کل سوالات</div><div class="card-value">{stats["questions_count"]}</div></div>', unsafe_allow_html=True)
                with sc2: st.markdown(f'<div class="custom-card"><div class="card-title">پژوهشگران</div><div class="card-value">{stats["users_count"]}</div></div>', unsafe_allow_html=True)
                most_active = "admin" 
                st.markdown(f'<div class="custom-card" style="padding: 40px 10px;"><div class="card-title">فعال‌ترین کاربر سیستم</div><div class="card-value-small">{most_active}</div></div>', unsafe_allow_html=True)
        else:
            tabs = st.tabs(["📂 بارگذاری سند", "📜 سوابق من"])
            with tabs[0]:
                files = st.file_uploader("انتخاب فایل‌های PDF", type="pdf", accept_multiple_files=True)
                if st.button("🔍 تحلیل هوشمند و استخراج نکات", use_container_width=True):
                    if files:
                        with st.spinner("در حال استخراج اطلاعات..."):
                            txt, _ = extract_text_from_pdfs(files)
                            st.session_state.pdf_text = txt
                            key_points = extract_important_sentences(txt)
                            st.success("تحلیل سند کامل شد.")
                            st.markdown("### 📌 نکات کلیدی سند شما:")
                            for point in key_points:
                                st.markdown(f"- {point}")
                    else:
                        st.error("لطفاً فایلی را برای تحلیل انتخاب کنید.")
            with tabs[1]:
                history = db.get_questions_for_user(user['username'], limit=8)
                for h in history: st.markdown(f"**س:** {h[0]} \n\n <small>{h[1]}</small>", unsafe_allow_html=True); st.divider()
