from openai import OpenAI
import os

def load_knowledge():
    try:
        with open("data.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "No information available"

def get_smart_reply(user_message):
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    knowledge = load_knowledge()
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a helpful customer service agent. Answer based on: {knowledge}"},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except:
        return "Sorry, there is a technical issue."
