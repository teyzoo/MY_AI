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
    body = json.dumps(
        data,
        ensure_ascii=False
    ).encode("utf-8")

    handler.send_response(status)
    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8"
    )
    handler.send_header(
        "Content-Length",
        str(len(body))
    )
    handler.end_headers()
    handler.wfile.write(body)


def ask_gemini(message, mode):
    if not GEMINI_API_KEY:
        return (
            "AI пока не подключён. "
            "Добавь GEMINI_API_KEY в переменные окружения сервера."
        )

    if mode == "project":
        system_prompt = """
Ты — Project Agent сервиса TEYZ.AI.

Ты занимаешься созданием программных проектов.

Пользователь может попросить создать:
- Telegram-бота;
- сайт;
- веб-приложение;
- Android-приложение;
- desktop-приложение;
- API;
- backend;
- database;
- другие программные проекты.

Твоя задача:

1. Понять требования.
2. Определить тип проекта.
3. Определить технологии.
4. Определить обязательные данные.
5. Запросить у пользователя только действительно необходимые данные.
6. Никогда не просить ненужные данные.
7. Секреты и токены не должны попадать непосредственно в исходный код.
8. Использовать переменные окружения для секретов.
9. После получения необходимых данных подготовить проект.
10. Проверить архитектуру и код.
11. Подготовить инструкции по запуску.

Если обязательных данных недостаточно — сначала задай вопросы.
Не начинай большую генерацию проекта, пока необходимые данные не получены.
"""
    else:
        system_prompt = """
Ты — TEYZ.AI.

Это обычный универсальный AI-чат.

Помогай пользователю:
- отвечать на вопросы;
- объяснять сложные темы;
- программировать;
- писать и редактировать тексты;
- переводить;
- анализировать информацию;
- разбирать изображения и документы, если они переданы;
- придумывать идеи;
- решать технические задачи.

Не превращай обычный чат в Project Agent без соответствующего запроса.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
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

        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:
            return "Gemini не вернул ответ."

        content = candidates[0].get(
            "content",
            {}
        )

        parts = content.get(
            "parts",
            []
        )

        answer = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        )

        if not answer:
            return "Gemini вернул пустой ответ."

        return answer

    except httpx.HTTPStatusError as error:
        try:
            details = error.response.json()

            return (
                "Ошибка Gemini:\n"
                + json.dumps(
                    details,
                    ensure_ascii=False
                )
            )
        except Exception:
            return (
                "Ошибка Gemini: "
                f"HTTP {error.response.status_code}"
            )

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
        self.send_header(
            "Content-Type",
            content_type
        )
        self.send_header(
            "Content-Length",
            str(len(data))
        )
        self.end_headers()

        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
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
                    "gemini": bool(
                        GEMINI_API_KEY
                    )
                }
            )
            return

        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw_body = self.rfile.read(
                content_length
            )

            data = json.loads(
                raw_body.decode("utf-8")
            )

            message = str(
                data.get(
                    "message",
                    ""
                )
            ).strip()

            mode = str(
                data.get(
                    "mode",
                    "chat"
                )
            ).strip()

            if not message:
                send_json(
                    self,
                    {
                        "error":
                        "Сообщение пустое."
                    },
                    400
                )
                return

            if mode not in (
                "chat",
                "project"
            ):
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
                {
                    "error":
                    "Некорректный JSON."
                },
                400
            )

        except Exception as error:
            send_json(
                self,
                {
                    "error": str(error)
                },
                500
            )


def main():
    server = ThreadingHTTPServer(
        (HOST, PORT),
        TEYZHandler
    )

    print("=" * 55)
    print("TEYZ.AI")
    print(
        f"Server: http://127.0.0.1:{PORT}"
    )
    print(
        f"Gemini model: {GEMINI_MODEL}"
    )
    print(
        f"Gemini configured: "
        f"{bool(GEMINI_API_KEY)}"
    )
    print("=" * 55)

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nTEYZ.AI остановлен.")

    finally:
        server.server_close()


if __name__ == "__main__":
    main()
