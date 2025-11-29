# -----------------------------
# 🚀 تشغيل البوت على Railway
# -----------------------------
import os
import uvicorn

@app.get("/")
async def home():
    return {"status": "alive", "message": "Bot is running!"}

if __name__ == "__main__":
    # Railway يعطي بورت في متغير PORT
    port = int(os.environ.get("PORT", 8080))  # fallback in case of local run
    print(f"🚀 Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
