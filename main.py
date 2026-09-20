from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import os

import httpx


BASE_DIR = Path(__file__).resolve().parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8000"))


SYSTEM_PROMPT = """
You are MY AI, a general-purpose AI assistant and coding agent.

Your abilities:
- answer questions;
- write Python, JavaScript, HTML, CSS and other code;
- explain code;
- create websites;
- create Telegram bots;
- design applications;
- debug programming errors;
- create project structures;
- help build complete software projects.

When the user asks to create software, provide practical
implementation and complete code when appropriate.

Be clear, useful and direct.
"""


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.end_headers()

        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            file = BASE_DIR / "index.html"

            if not file.exists():
                self.send_json(
                    {
                        "error": "index.html not found"
                    },
                    404
                )
                return

            body = file.read_bytes()

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.end_headers()

            self.wfile.write(body)

            return

        if path == "/api/health":
            self.send_json({
                "status": "ok",
                "ai": "gemini",
                "model": GEMINI_MODEL,
                "api_key": bool(GEMINI_API_KEY)
            })

            return

        self.send_json(
            {
                "error": "Not found"
            },
            404
        )

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/chat":
            self.send_json(
                {
                    "error": "Not found"
                },
                404
            )
            return

        if not GEMINI_API_KEY:
            self.send_json(
                {
                    "error": "GEMINI_API_KEY не установлен"
                },
                500
            )
            return

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw = self.rfile.read(length)

            data = json.loads(
                raw.decode("utf-8")
            )

        except Exception:
            self.send_json(
                {
                    "error": "Invalid JSON"
                },
                400
            )
            return

        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        if not message:
            self.send_json(
                {
                    "error": "Message is empty"
                },
                400
            )
            return

        prompt = (
            SYSTEM_PROMPT
            + "\n\n"
            + "User request:\n"
            + message
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        try:
            with httpx.Client(
                timeout=120
            ) as client:

                response = client.post(
                    GEMINI_URL,
                    params={
                        "key": GEMINI_API_KEY
                    },
                    json=payload
                )

                response.raise_for_status()

                result = response.json()

            candidates = result.get(
                "candidates",
                []
            )

            answer = ""

            if candidates:

                content = candidates[0].get(
                    "content",
                    {}
                )

                parts = content.get(
                    "parts",
                    []
                )

                for part in parts:

                    text = part.get(
                        "text",
                        ""
                    )

                    if text:
                        answer += text

            answer = answer.strip()

            if not answer:
                answer = (
                    "Gemini не вернул текстовый ответ."
                )

            self.send_json({
                "answer": answer
            })

        except httpx.HTTPStatusError as error:

            try:
                error_data = error.response.json()

                error_message = (
                    error_data
                    .get("error", {})
                    .get(
                        "message",
                        "Ошибка Gemini API"
                    )
                )

            except Exception:
                error_message = (
                    "Ошибка Gemini API"
                )

            print(
                "Gemini API error:",
                error_message
            )

            self.send_json(
                {
                    "error": error_message
                },
                502
            )

        except Exception as error:

            print(
                "Gemini connection error:",
                error
            )

            self.send_json(
                {
                    "error": (
                        "Не удалось подключиться "
                        "к Gemini API"
                    )
                },
                503
            )

    def log_message(self, format, *args):
        print(
            f"[MY AI] {format % args}"
        )


def main():

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler
    )

    print(
        f"MY AI запущен на "
        f"http://{HOST}:{PORT}"
    )

    print(
        f"AI: Gemini / {GEMINI_MODEL}"
    )

    print(
        "API key:",
        "OK" if GEMINI_API_KEY else "NOT SET"
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:

        print(
            "\nMY AI остановлен."
        )

    finally:

        server.server_close()


if __name__ == "__main__":
    main()
