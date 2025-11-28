from fastapi import FastAPI, Request, HTTPException
from ai import get_smart_reply
import os
import requests

app = FastAPI()

@app.get("/webhook")
def verify(request: Request):
    token = os.environ.get("FACEBOOK_VERIFY_TOKEN")
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and verify_token == token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    if data.get("object") == "page":
        for entry in data["entry"]:
            for msg in entry.get("messaging", []):
                sender_id = msg.get("sender", {}).get("id")
                if "message" in msg and "text" in msg["message"]:
                    user_text = msg["message"]["text"]
                    reply = get_smart_reply(user_text)
                    send_to_facebook(sender_id, reply)
    return "ok"

def send_to_facebook(user_id, text):
    page_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={page_token}"
    payload = {"recipient": {"id": user_id}, "message": {"text": text}}
    requests.post(url, json=payload)
