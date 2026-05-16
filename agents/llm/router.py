from typing import List, Dict
import logging
from llm.gemini import complete_gemini
from llm.openai import complete_openai, embed_openai
from llm.local import complete_local

logger = logging.getLogger(__name__)

class ModelRouter:
    ROUTING_TABLE = {
        "code_analysis": "gemini-1.5-pro",
        "log_extraction": "gemini-1.5-flash",
        "repair_generation": "gpt-4o",
        "web_synthesis": "gpt-4o-mini",
        "embedding": "text-embedding-3-small",
        "fallback": "ollama/llama3",
    }

    async def complete(self, task_type: str, messages: List[Dict[str, str]], response_format: str = "text") -> str:
        model_name = self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["fallback"])
        
        try:
            if "gemini" in model_name:
                return await complete_gemini(model_name, messages, response_format)
            elif "gpt" in model_name:
                return await complete_openai(model_name, messages, response_format)
            elif "ollama" in model_name or "llama" in model_name:
                return await complete_local(model_name, messages, response_format)
            else:
                # Default to OpenAI if unknown but follows gpt naming, or fallback
                return await complete_openai(model_name, messages, response_format)
        except Exception as e:
            logger.error(f"Primary model {model_name} failed for {task_type}: {e}")
            if model_name != self.ROUTING_TABLE["fallback"]:
                logger.info(f"Falling back to {self.ROUTING_TABLE['fallback']}")
                return await complete_local(self.ROUTING_TABLE["fallback"], messages, response_format)
            raise e

    async def embed(self, text: str) -> List[float]:
        model_name = self.ROUTING_TABLE["embedding"]
        try:
            return await embed_openai(model_name, text)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            # No easy local embedding fallback implemented yet in local.py
            # Return empty list or zero vector as last resort
            return [0.0] * 1536
