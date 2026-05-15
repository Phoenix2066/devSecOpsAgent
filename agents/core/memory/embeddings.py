async def embed_error_signature(text: str) -> list[float]:
    values = [float((ord(ch) % 31) / 31) for ch in text[:32]]
    return values + [0.0] * (32 - len(values))
