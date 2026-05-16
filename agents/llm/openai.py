from openai import AsyncOpenAI
from config import settings

async def get_openai_client():
    return AsyncOpenAI(api_key=settings.openai_api_key)

async def complete_openai(model_name: str, messages: list[dict], response_format: str = "text") -> str:
    client = await get_openai_client()
    
    kwargs = {
        "model": model_name,
        "messages": messages,
    }
    
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}
    
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

async def embed_openai(model_name: str, text: str) -> list[float]:
    client = await get_openai_client()
    response = await client.embeddings.create(
        input=[text],
        model=model_name
    )
    return response.data[0].embedding
