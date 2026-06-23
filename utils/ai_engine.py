from openai import OpenAI, APIConnectionError
import re
import time



# ---------------------------
# تنظیم Client به صورت صحیح
# ---------------------------
CLIENT = OpenAI(
    base_url="https://api.gapgpt.app/v1",
    api_key="sk-k4ZiAJxRmxia4xD0rDb2cX3NAU9WAFp0X4cUHnzjn3lkGmUU"
)

MODEL_NAME = "gpt-4o"

def test_api_key():
    try:
        CLIENT.models.list()
        return True
    except Exception:
        return False


# ---------------------------
# نرمال‌سازی متن
# ---------------------------
def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------
# تکه‌تکه کردن متن برای RAG
# ---------------------------
def chunk_text(text: str, chunk_size=1800, overlap=250):
    chunks = []
    i = 0
    n = len(text)

    while i < n:
        chunks.append(text[i:i + chunk_size])
        i += max(1, chunk_size - overlap)

    return chunks


# ---------------------------
# امتیازدهی چانک‌ها
# ---------------------------
def score_chunk(chunk: str, query: str) -> int:
    c = normalize_text(chunk)
    q = normalize_text(query)

    words = [w for w in q.split() if len(w) >= 2]

    score = 0
    for w in words:
        score += c.count(w)

    return score


# ---------------------------
# بازیابی بخش مرتبط از PDF
# ---------------------------
def retrieve_relevant(document_text: str, query: str, top_k=4) -> str:
    chunks = chunk_text(document_text, chunk_size=1800, overlap=250)
    scored = [(score_chunk(ch, query), ch) for ch in chunks]
    scored.sort(key=lambda x: x[0], reverse=True)

    picked = [ch for sc, ch in scored[:top_k] if sc > 0]

    if not picked:
        picked = chunks[:2]  # fallback

    return "\n\n".join(picked)


# ---------------------------
# تولید پاسخ چت (با سیستم ضد‌قطع)
# ---------------------------
def generate_chat_response(messages, document_text: str):
    user_query = messages[-1]["content"]
    relevant_text = retrieve_relevant(document_text, user_query, top_k=4)

    system_instruction = (
        "شما یک دستیار آموزشی خیلی دقیق و حرفه‌ای هستید.\n"
        "فقط بر اساس «متن مرجع» پاسخ بده.\n"
        "اگر پاسخ در فایل نیست، بنویس:\n"
        "«این پاسخ به‌صورت مستقیم در فایل ارسالی یافت نشد.»\n"
        "پاسخ‌ها باید فارسی، دقیق و مستند باشند.\n"
    )

    recent = messages[-8:] if len(messages) > 8 else messages

    api_messages = [
        {"role": "system", "content": system_instruction},
        {"role": "system", "content": f"متن مرجع مرتبط:\n{relevant_text}"},
        *recent
    ]

    # سیستم Retry (سه تلاش)
    for attempt in range(3):
        try:
            resp = CLIENT.chat.completions.create(
                model=MODEL_NAME,
                messages=api_messages,
                temperature=0.2
            )
            return resp.choices[0].message.content

        except APIConnectionError:
            time.sleep(1.2)

    # اگر ۳ بار شکست خورد
    return "❌ ارتباط با سرور هوش مصنوعی برقرار نشد. لطفاً چند لحظه بعد تلاش کنید."


# ---------------------------
# استخراج ۵ نکته مهم از PDF
# ---------------------------
def extract_important_sentences(document_text: str):
    short_text = (document_text or "")[:6000]

    prompt = (
        "از متن زیر 5 نکته مهم و کاربردی استخراج کن.\n"
        "خروجی باید فارسی و شماره‌دار باشد:\n\n"
        f"{short_text}"
    )

    for attempt in range(3):
        try:
            resp = CLIENT.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            lines = [l.strip() for l in resp.choices[0].message.content.split("\n") if l.strip()]
            return lines[:5]

        except APIConnectionError:
            time.sleep(1.2)

    return ["❌ تحلیل سند انجام نشد. دوباره تلاش کنید."]
