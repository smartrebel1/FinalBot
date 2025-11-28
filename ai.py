import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

def load_knowledge():
    try:
        with open("data.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "No information available"

def get_smart_reply(user_message):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            logger.error("GEMINI_API_KEY not found")
            return "Sorry, there is a technical issue."
        
        genai.configure(api_key=api_key)
        knowledge = load_knowledge()
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""You are a helpful customer service agent for Misr Sweets, an Egyptian confectionery business.
        
Knowledge Base:
{knowledge}

User Message: {user_message}

Please respond in Arabic/Egyptian if the user writes in Arabic. Provide helpful, friendly responses based on the knowledge base."""
        
        response = model.generate_content(prompt)
        logger.info(f"Gemini response generated")
        
        return response.text
    except Exception as e:
        logger.error(f"Error in get_smart_reply: {str(e)}", exc_info=True)
        return "Sorry, there is a technical issue."
