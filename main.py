import os
import logging
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import google.generativeai as genai
import uvicorn

# ======================================================
# 1) Logging
# ======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ======================================================
# 2) Load ENV Variables
# ======================================================
load_dotenv()

FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ======================================================
# 3) Configure Gemini
# ======================================================
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    logger.info("✅ Gemini configured successfully")
else:
    logger.error("❌ Missing GEMINI_API_KEY")

# ======================================================
# 4) Initialize FastAPI App
# ======================================================
app = FastAPI()

# ======================================================
# 5) Health Check (Railway Needs This)
# ======================================================
@app.get("/")
async def home():
    return {"status": "alive", "message": "Bot running successfully"}

# ======================================================
# 6) Webhook Verification
# ======================================================
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == FACEBOOK_VERIFY_TOKEN:
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")

    return {"status": "missing_params"}

# ======================================================
# 7) Receive Messages
# ======================================================
@app.post("/webhook")
async def webhook_handler(request: Request):
    body = await request.json()

    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for event in entry.get("messaging", []):

                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    text = event["message"]["text"]

                    reply = generate_reply(text)
                    send_message(sender_id, reply)

        return JSONResponse({"status": "ok"}, status_code=200)

    raise HTTPException(status_code=404, detail="Not a page event")

# ======================================================
# 8) AI Reply
# ======================================================
def generate_reply(user_text):
    company_data = ""

    if os.path.exists("data.txt"):
        with open("data.txt", "r", encoding="utf-8") as f:
            company_data = f.read()

    prompt = f"""
    أنت مساعد خدمة عملاء لــ "حلويات مصر".
    استخدم البيانات التالية:
    {company_data}

    - جاوب باختصار وبأسلوب محترم جدًا.
    - استخدم لهجة مصرية بسيطة.
    - لا تخترع معلومات غير موجودة.

    سؤال العميل: {user_text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "حاضر يا فندم، بس فيه مشكلة بسيطة دلوقتي. حاول تاني بعد دقيقة ❤️"

# ======================================================
# 9) Send reply to Facebook
# ======================================================
def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }

    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            logger.error(f"FB Error: {r.text}")
    except Exception as e:
        logger.error(f"FB send error: {e}")

# ======================================================
# 10) Start App (Railway)
# ======================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
