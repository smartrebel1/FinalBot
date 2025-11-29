import os
import logging
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import google.generativeai as genai
import uvicorn
from dotenv import load_dotenv

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    logger.error("NO GEMINI API KEY FOUND!")

app = FastAPI()

# -------------------------
# MAIN HEALTH CHECK (FIX)
# -------------------------
@app.get("/")
async def home():
    return {"status": "alive", "msg": "Bot running successfully"}

# -------------------------
# VERIFY FACEBOOK WEBHOOK
# -------------------------
@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == FACEBOOK_VERIFY_TOKEN:
        return int(challenge)
    else:
        raise HTTPException(status_code=403)

# -------------------------
# MESSAGE HANDLER
# -------------------------
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    if body.get("object") == "page":
        for entry in body["entry"]:
            for messaging_event in entry["messaging"]:
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    sender = messaging_event["sender"]["id"]
                    text = messaging_event["message"]["text"]
                    reply = ai_reply(text)
                    send_fb_message(sender, reply)

    return JSONResponse({"status": "ok"})

# -------------------------
# AI REPLY
# -------------------------
def ai_reply(user_text):
    try:
        data = ""
        if os.path.exists("data.txt"):
            data = open("data.txt", encoding="utf8").read()

        prompt = f"""
        انت بوت خدمة عملاء حلويات مصر.
        استخدم المعلومات التالية فقط:

        {data}

        رد على سؤال العميل: {user_text}
        """

        result = model.generate_content(prompt)
        return result.text.strip()
    except:
        return "حصل مشكلة مؤقتاً يا فندم، حاول تاني ❤️"

# -------------------------
# SEND TO FACEBOOK
# -------------------------
def send_fb_message(user, text):
    url = f"https://graph.facebook.com/v19.0/me/messages"
    params = {"access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    data = {"recipient": {"id": user}, "message": {"text": text}}
    requests.post(url, params=params, json=data)

# -------------------------
# FORCE RAILWAY PORT FIX
# -------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
