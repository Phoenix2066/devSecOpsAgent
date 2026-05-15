class ModelRouter:
    ROUTING_TABLE = {
        "code_analysis": "gemini-1.5-pro",
        "log_extraction": "gemini-1.5-flash",
        "repair_generation": "gpt-4o",
        "web_synthesis": "gpt-4o-mini",
        "embedding": "text-embedding-3-small",
        "fallback": "ollama/llama3",
    }

    async def complete(self, task_type: str, messages: list[dict], response_format: str = "text") -> str:
        if response_format == "json":
            return "{}"
        return f"mock completion for {task_type}"

    async def embed(self, text: str) -> list[float]:
        return [0.0] * 1536
