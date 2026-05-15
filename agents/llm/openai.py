async def complete(messages: list[dict]) -> str:
    return "mock openai response"


async def embed(text: str) -> list[float]:
    return [0.0] * 1536
