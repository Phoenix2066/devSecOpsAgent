from fastapi import FastAPI

from api.routes import router

app = FastAPI(title="Anvil Agent Runtime", version="0.1.0")
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
