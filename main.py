import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx


BASE_DIR = Path(__file__).resolve().parent
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


def send_json(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def ask_gemini(message, mode="chat"):
    if not GEMINI_API_KEY:
        return "Gemini API пока не подключён. Добавь GEMINI_API_KEY в переменные окружения."

    if mode == "project":
        system_prompt = """
Ты — Project Agent сервиса TEYZ.AI.

Твоя задача — помогать создавать программные проекты.
Ты должен:
1. Понять задачу пользователя.
2. Определить тип проекта.
3. Определить необходимые технологии.
4. Определить данные, которые потребуются от пользователя.
5. Не просить ненужные данные.
6. Если нужны секреты, никогда не вставлять их непосредственно в исходный код.
7. Использовать переменные окружения для токенов и API-ключей.
8. После получения всех необходимых данных подготовить проект.

Если для создания проекта не хватает обязательных данных, сначала перечисли только необходимые данные и попроси пользователя их предоставить.
"""
    else:
        system_prompt = """
Ты — TEYZ.AI, современный универсальный AI-помощник.
Отвечай понятно, точно и полезно.
Ты умеешь работать с обычными вопросами, текстом, программированием,
объяснениями, анализом информации и другими задачами пользователя.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": system_prompt
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": message
                    }
                ]
            }
        ]
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=120
        )

        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            return "Gemini не вернул ответ."

        parts = candidates[0].get("content", {}).get("parts", [])

        answer = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        )

        return answer or "Gemini вернул пустой ответ."

    except httpx.HTTPStatusError as error:
        try:
            details = error.response.json()
            return f"Ошибка Gemini: {json.dumps(details, ensure_ascii=False)}"
        except Exception:
            return f"Ошибка Gemini: HTTP {error.response.status_code}"

    except Exception as error:
        return f"Ошибка соединения с Gemini: {error}"


class TEYZHandler(BaseHTTPRequestHandler):

    def send_file(self, filename, content_type):
        path = BASE_DIR / filename

        if not path.exists():
            self.send_error(404)
            return

        data = path.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_file(
                "index.html",
                "text/html; charset=utf-8"
            )
            return

        if self.path == "/api/health":
            send_json(
                self,
                {
                    "ok": True,
                    "service": "TEYZ.AI",
                    "gemini_configured": bool(GEMINI_API_KEY)
                }
            )
            return

        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)

            data = json.loads(raw_body.decode("utf-8"))

            message = str(data.get("message", "")).strip()
            mode = str(data.get("mode", "chat")).strip()

            if not message:
                send_json(
                    self,
                    {"error": "Сообщение пустое."},
                    400
                )
                return

            if mode not in ("chat", "project"):
                mode = "chat"

            answer = ask_gemini(
                message,
                mode
            )

            send_json(
                self,
                {
                    "ok": True,
                    "answer": answer,
                    "mode": mode
                }
            )

        except json.JSONDecodeError:
            send_json(
                self,
                {"error": "Некорректный JSON."},
                400
            )

        except Exception as error:
            send_json(
                self,
                {"error": str(error)},
                500
            )


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        (HOST, PORT),
        TEYZHandler
    )

    print("=" * 50)
    print("TEYZ.AI")
    print(f"Server: http://127.0.0.1:{PORT}")
    print(f"Gemini model: {GEMINI_MODEL}")
    print(f"Gemini configured: {bool(GEMINI_API_KEY)}")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nTEYZ.AI остановлен.")
    finally:
        server.server_close()
