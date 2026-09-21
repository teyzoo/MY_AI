import os
import json
import httpx
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = 8000

LLAMA_URL = os.getenv(
    "LLAMA_URL",
    "http://127.0.0.1:8080"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")


def qwen_request(message):
    url = f"{LLAMA_URL}/v1/chat/completions"

    payload = {
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "temperature": 0.7,
        "max_tokens": 512,
        "stream": False
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=120.0
        )

        data = response.json()

        if response.status_code != 200:
            return {
                "error": data.get(
                    "error",
                    f"Qwen API error: HTTP {response.status_code}"
                )
            }

        choices = data.get("choices", [])

        if not choices:
            return {
                "error": "Qwen3 не вернул ответ"
            }

        message_data = choices[0].get(
            "message",
            {}
        )

        answer = message_data.get(
            "content",
            ""
        ).strip()

        if not answer:
            return {
                "error": "Qwen3 вернул пустой ответ"
            }

        return {
            "answer": answer
        }

    except httpx.ConnectError:
        return {
            "error": (
                "Не удалось подключиться к Qwen3. "
                "Проверь, запущен ли llama-server."
            )
        }

    except httpx.TimeoutException:
        return {
            "error": "Qwen3 слишком долго отвечает"
        }

    except Exception as e:
        return {
            "error": f"Ошибка Qwen3: {str(e)}"
        }


class MyAIHandler(BaseHTTPRequestHandler):

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

    def do_OPTIONS(self):
        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/health":
            qwen_online = False

            try:
                response = httpx.get(
                    f"{LLAMA_URL}/health",
                    timeout=5.0
                )

                qwen_online = (
                    response.status_code == 200
                )

            except Exception:
                qwen_online = False

            self.send_json({
                "status": "ok",
                "ai": "Qwen3",
                "model": "Qwen3-1.7B-Q4_K_M",
                "qwen_server": qwen_online
            })

            return

        if path == "/":
            try:
                with open(
                    INDEX_FILE,
                    "rb"
                ) as file:
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
                self.send_error(
                    404,
                    "index.html не найден"
                )

            return

        self.send_error(
            404,
            "Not Found"
        )

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
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw_body = self.rfile.read(length)

            data = json.loads(
                raw_body.decode("utf-8")
            )

            message = data.get(
                "message",
                ""
            ).strip()

            if not message:
                self.send_json(
                    {
                        "error": "Пустое сообщение"
                    },
                    400
                )
                return

            result = qwen_request(
                message
            )

            self.send_json(result)

        except json.JSONDecodeError:
            self.send_json(
                {
                    "error": "Некорректный JSON"
                },
                400
            )

        except Exception as e:
            self.send_json(
                {
                    "error": str(e)
                },
                500
            )


if __name__ == "__main__":
    print(
        f"TEYZ.AI server запущен "
        f"на http://{HOST}:{PORT}"
    )

    print(
        f"AI: Qwen3-1.7B-Q4_K_M"
    )

    print(
        f"Qwen server: {LLAMA_URL}"
    )

    server = ThreadingHTTPServer(
        (HOST, PORT),
        MyAIHandler
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nTEYZ.AI остановлен")

        server.server_close()
        
