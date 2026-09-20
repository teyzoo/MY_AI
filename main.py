from pathlib import Path
import os
import json

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434"
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "qwen2.5:3b"
)

app = FastAPI(title="MY AI")


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": AI_MODEL
    }


@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON"
        )

    message = str(data.get("message", "")).strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message is empty"
        )

    prompt = f"""
You are MY AI.

You are a general-purpose AI assistant and coding agent.

You can:
- answer questions;
- write Python, JavaScript, HTML, CSS and other code;
- explain code;
- design applications;
- help create complete projects;
- find and fix programming errors;
- create project structures;
- help build websites, bots and applications.

When the user asks to create software, provide practical implementation
and complete code when appropriate.

User request:

{message}
"""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": AI_MODEL,
                    "prompt": prompt,
                    "stream": False
                }
            )

            response.raise_for_status()

            result = response.json()
            answer = result.get("response", "").strip()

            if not answer:
                answer = "Модель не вернула ответ."

            return {
                "answer": answer
            }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI-модель пока не подключена."
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
    
