import httpx
from config import settings
import logging

logger = logging.getLogger(__name__)

async def complete_local(model_name: str, messages: list[dict], response_format: str = "text") -> str:
    # Assuming Ollama
    url = f"{settings.ollama_base_url}/api/chat"
    
    # model_name might be 'ollama/llama3', strip the prefix
    model = model_name.split("/")[-1] if "/" in model_name else model_name
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    
    if response_format == "json":
        payload["format"] = "json"
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            return ""
