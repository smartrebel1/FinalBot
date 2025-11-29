import os
import logging
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import google.generativeai as genai
import uvicorn

# ===========================
# 1) Logging
# ===========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===========================
# 2) Load ENV Variables
# ===========================
load_dotenv()

FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ===========================
# 3) Config Gemini AI
# ===========================
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    logger.info("✅ Gemini AI configured successfully")
else:
    logger.error("❌ Missing GEMINI_API_KEY")

# ===========================
# 4) Initialize App
# ===========================
app = FastAPI()

# ===========================
# 5) Health Check (Required by Railway)
# ===========================
@app.get("/")
async def home():
    return {"status": "alive", "message": "Bot running on Railway successfully!"}

# ===========================
# 6) Facebook Webhook Verification
# ===========================
@app.get("/webhook")
async def verify_token(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == FACEBOOK_VERIFY_TOKEN:
            logger.info("✅ Webhook verified by Facebook")
            return int(challenge)
        else:
            logger.warning("❌ Invalid Verify Token")
            raise HTTPException(status_code=403, detail="Verification failed")

    return {"status": "error", "message": "Missing params"}

# ===========================
# 7) Receive Messages
# ===========================
@app.post("/webhook")
async def receive_message(request: Request):
    try:
        body = await request.json()

        if body.get("object") == "page":
            for entry in body.get("entry", []):
                for msg_event in entry.get("messaging", []):

                    # رسالة من المستخدم
                    if "message" in msg_event and "text" in msg_event["message"]:
                        sender_id = msg_event["sender"]["id"]
                        user_text = msg_event["message"]["text"]

                        logger.info(f"👤 User ({sender_id}): {user_text}")

                        ai_reply = generate_reply(user_text)
                        send_message(sender_id, ai_reply)

            return JSONResponse({"status": "received"}, status_code=200)

        else:
            raise HTTPException(status_code=404, detail="Not a FB page event")

    except Exception as e:
        logger.error(f"💥 Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ===========================
# 8) AI Response
# ===========================
def generate_reply(user_text):

    # Read company info from data.txt
    info = ""
    if os.path.exists("data.txt"):
        with open("data.txt", "r", encoding="utf-8") as f:
            info = f.read()

    prompt = f"""
    أنت مساعد خدمة عملاء لــ "حلويات مصر".
    هذه بيانات الشركة:
    {info}

    - أجب بإيجاز ولباقة باللهجة المصرية.
    - التزم بالمعلومات فقط.
    - لا تخترع أسعار أو خدمات.
    
    سؤال العميل: {user_text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "عذراً، فيه مشكلة مؤقتة. حاول تاني ❤️"

# ===========================
# 9) Send Message to Facebook
# ===========================
def send_message(user_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"

    payload = {
        "recipient": {"id": user_id},
        "message": {"text": text}
    }

    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            logger.info(f"📤 Sent: {text[:40]}")
        else:
            logger.error(f"FB Error: {res.text}")

    except Exception as e:
        logger.error(f"FB Connection Error: {e}")

# ===========================
# 10) Start App (Railway)
# ===========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
