import os
import logging
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import google.generativeai as genai
import uvicorn
from dotenv import load_dotenv

# 1. إعداد السجلات (Logging) لنرى ماذا يحدث في Railway
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 2. تحميل متغيرات البيئة
load_dotenv()

FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# إعداد Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # نستخدم موديل flash لأنه سريع ومناسب للشات بوت
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("✅ Google Gemini Configured Successfully")
else:
    logger.error("❌ GEMINI_API_KEY is missing!")

app = FastAPI()

# ---------------------------------------------------------
# ✅ الإصلاح الأساسي: نقطة النهاية الرئيسية (Health Check)
# هذا ما يبحث عنه Railway ليتأكد أن البوت يعمل
# ---------------------------------------------------------
@app.get("/")
async def home():
    return {"status": "active", "message": "Bot is running perfectly on Railway!"}

# ---------------------------------------------------------
# 3. التحقق من الويب هوك (Facebook Verification)
# ---------------------------------------------------------
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == FACEBOOK_VERIFY_TOKEN:
            logger.info("✅ Webhook Verified Successfully!")
            return int(challenge)
        else:
            logger.warning("❌ Verification Failed: Invalid Token")
            raise HTTPException(status_code=403, detail="Verification failed")
    return {"status": "error", "message": "Missing parameters"}

# ---------------------------------------------------------
# 4. استقبال الرسائل (POST)
# ---------------------------------------------------------
@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        body = await request.json()
        # logger.info(f"📩 Event Received: {body}")  # (اختياري: لتخفيف الزحمة في السجلات)

        if body.get("object") == "page":
            for entry in body.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    
                    # التأكد أن الحدث هو رسالة وليس شيئاً آخر (مثل delivery status)
                    if "message" in messaging_event and "text" in messaging_event["message"]:
                        sender_id = messaging_event["sender"]["id"]
                        user_message = messaging_event["message"]["text"]
                        
                        logger.info(f"👤 User ({sender_id}) says: {user_message}")

                        # 1. توليد الرد من الذكاء الاصطناعي
                        bot_reply = get_ai_response(user_message)
                        
                        # 2. إرسال الرد إلى فيسبوك
                        send_message(sender_id, bot_reply)

            return JSONResponse(content={"status": "EVENT_RECEIVED"}, status_code=200)
        else:
            raise HTTPException(status_code=404, detail="Not a page event")
            
    except Exception as e:
        logger.error(f"💥 Error processing webhook: {str(e)}")
        return JSONResponse(content={"status": "error"}, status_code=500)

# ---------------------------------------------------------
# 5. دالة الذكاء الاصطناعي (Gemini)
# ---------------------------------------------------------
def get_ai_response(user_text):
    try:
        # قراءة بيانات الشركة من الملف
        data_content = ""
        if os.path.exists("data.txt"):
            with open("data.txt", "r", encoding="utf-8") as f:
                data_content = f.read()
        else:
            logger.warning("⚠️ data.txt file not found!")

        # تجهيز التلقين (Prompt)
        prompt = f"""
        أنت مساعد ذكي لخدمة عملاء شركة "Misr Sweets".
        معلومات الشركة:
        {data_content}

        تعليمات:
        - أجب بناءً على المعلومات أعلاه فقط.
        - كن ودوداً ومختصراً.
        - تحدث باللهجة المصرية أو العربية الفصحى البسيطة.
        
        سؤال العميل: {user_text}
        """

        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"🤖 AI Error: {str(e)}")
        return "عذراً، أواجه مشكلة تقنية حالياً. يرجى المحاولة لاحقاً."

# ---------------------------------------------------------
# 6. دالة إرسال الرد لفيسبوك
# ---------------------------------------------------------
def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"📤 Sent to Facebook: {text[:50]}...")
        else:
            logger.error(f"❌ Failed to send to FB: {response.text}")
    except Exception as e:
        logger.error(f"❌ Connection Error sending to FB: {str(e)}")

# ---------------------------------------------------------
# 7. نقطة الانطلاق (تشغيل السيرفر)
# ✅ هذا الجزء هو الذي يصلح مشكلة Railway Port
# ---------------------------------------------------------
if __name__ == "__main__":
    # الحصول على المنفذ من متغيرات البيئة أو استخدام 8080 كاحتياطي
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting Server on Port: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
