from fastapi import FastAPI, Request, HTTPException
from ai import get_smart_reply
import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/webhook")
def verify(request: Request):
    token = os.environ.get("FACEBOOK_VERIFY_TOKEN")
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    logger.info(f"Webhook verification request - mode: {mode}")
    
    if mode == "subscribe" and verify_token == token:
        logger.info("Webhook verified successfully")
        return int(challenge)
    
    logger.error("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Webhook received data")
        
        if data.get("object") == "page":
            for entry in data["entry"]:
                for msg in entry.get("messaging", []):
                    sender_id = msg.get("sender", {}).get("id")
                    logger.info(f"Processing message from sender: {sender_id}")
                    
                    if "message" in msg and "text" in msg["message"]:
                        user_text = msg["message"]["text"]
                        logger.info(f"User message: {user_text}")
                        
                        reply = get_smart_reply(user_text)
                        logger.info(f"AI reply: {reply}")
                        
                        send_result = send_to_facebook(sender_id, reply)
                        logger.info(f"Send result: {send_result}")
        
        return "ok"
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return "ok"

def send_to_facebook(user_id, text):
    try:
        page_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
        logger.info(f"Page token exists: {bool(page_token)}")
        
        if not page_token:
            logger.error("FACEBOOK_PAGE_ACCESS_TOKEN not found")
            return {"error": "Missing page token"}
        
        url = f"https://graph.facebook.com/v18.0/me/messages?access_token={page_token}"
        payload = {"recipient": {"id": user_id}, "message": {"text": text}}
        
        logger.info(f"Sending to user {user_id}")
        
        response = requests.post(url, json=payload)
        logger.info(f"Facebook response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Failed. Status: {response.status_code}, Response: {response.text}")
            return {"error": response.text}
        
        logger.info("Message sent successfully")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error in send_to_facebook: {str(e)}", exc_info=True)
        return {"error": str(e)}
