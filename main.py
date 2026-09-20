from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import httpx

BASE_DIR = Path(__file__).resolve().parent

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434"
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "qwen2.5:3b"
)

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8000"))


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
                    {"error": "index.html not found"},
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
                "model": AI_MODEL
            })
            return

        self.send_json(
            {"error": "Not found"},
            404
        )

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/chat":
            self.send_json(
                {"error": "Not found"},
                404
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
            data = json.loads(raw.decode("utf-8"))

        except Exception:
            self.send_json(
                {"error": "Invalid JSON"},
                400
            )
            return

        message = str(
            data.get("message", "")
        ).strip()

        if not message:
            self.send_json(
                {"error": "Message is empty"},
                400
            )
            return

        prompt = f"""
You are MY AI.

You are a general-purpose AI assistant
and coding agent.

You can:
- answer questions;
- write code;
- explain code;
- create applications;
- create websites;
- create Telegram bots;
- debug programming errors;
- design project structures;
- help build complete software projects.

Give practical answers and complete code
when appropriate.

User request:

{message}
"""

        try:
            with httpx.Client(timeout=120) as client:

                response = client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": AI_MODEL,
                        "prompt": prompt,
                        "stream": False
                    }
                )

                response.raise_for_status()

                result = response.json()

            answer = str(
                result.get(
                    "response",
                    ""
                )
            ).strip()

            if not answer:
                answer = "Модель не вернула ответ."

            self.send_json({
                "answer": answer
            })

        except Exception as error:

            self.send_json({
                "error": (
                    "AI-модель пока не подключена."
                )
            }, 503)

            print(
                "AI error:",
                error
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
        f"AI model: {AI_MODEL}"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMY AI остановлен.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
