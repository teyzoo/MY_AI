import os
import json
import httpx
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


HOST = "0.0.0.0"
PORT = 8000

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")


def gemini_request(message):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY не установлен"}

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )

    payload = {
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
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=120.0
        )

        data = response.json()

        if response.status_code != 200:
            error = data.get("error", {})
            return {
                "error": error.get(
                    "message",
                    f"Gemini API error: HTTP {response.status_code}"
                )
            }

        candidates = data.get("candidates", [])

        if not candidates:
            return {"error": "Gemini не вернул ответ"}

        parts = candidates[0].get("content", {}).get("parts", [])

        answer = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        ).strip()

        if not answer:
            return {"error": "Gemini вернул пустой ответ"}

        return {"answer": answer}

    except httpx.TimeoutException:
        return {"error": "Превышено время ожидания Gemini API"}

    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}


class MyAIHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/health":
            self.send_json({
                "status": "ok",
                "ai": "Gemini",
                "model": GEMINI_MODEL,
                "api_key": bool(GEMINI_API_KEY)
            })
            return

        if path == "/":
            try:
                with open(INDEX_FILE, "rb") as file:
                    content = file.read()

                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
                )
                self.send_header(
                    "Content-Length",
                    str(len(content))
                )
                self.end_headers()

                self.wfile.write(content)

            except FileNotFoundError:
                self.send_error(404, "index.html не найден")

            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/chat":
            self.send_json(
                {"error": "Not Found"},
                404
            )
            return

        try:
            length = int(
                self.headers.get("Content-Length", "0")
            )

            raw_body = self.rfile.read(length)
            data = json.loads(raw_body.decode("utf-8"))

            message = data.get("message", "").strip()

            if not message:
                self.send_json(
                    {"error": "Пустое сообщение"},
                    400
                )
                return

            result = gemini_request(message)

            self.send_json(result)

        except json.JSONDecodeError:
            self.send_json(
                {"error": "Некорректный JSON"},
                400
            )

        except Exception as e:
            self.send_json(
                {"error": str(e)},
                500
            )


if __name__ == "__main__":
    print(f"MY AI запущен на http://{HOST}:{PORT}")
    print(f"AI: Gemini / {GEMINI_MODEL}")
    print(
        "API key: "
        + ("OK" if GEMINI_API_KEY else "NOT SET")
    )

    server = ThreadingHTTPServer(
        (HOST, PORT),
        MyAIHandler
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMY AI остановлен")
        server.server_close()
