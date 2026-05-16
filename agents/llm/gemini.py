import google.generativeai as genai
from config import settings

def get_gemini_model(model_name: str):
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(model_name)

async def complete_gemini(model_name: str, messages: list[dict], response_format: str = "text") -> str:
    model = get_gemini_model(model_name)
    
    # Convert messages to Gemini format
    # Simple conversion: combine messages into a single prompt for now or use ChatSession
    prompt = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prompt += f"{role}: {content}\n"
    
    generation_config = {}
    if response_format == "json":
        generation_config["response_mime_type"] = "application/json"
    
    response = await model.generate_content_async(prompt, generation_config=generation_config)
    return response.text
