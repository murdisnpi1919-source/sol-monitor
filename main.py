import threading
import time
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import bingx_monitor
import person_monitor


def monitor_loop():
    print("🚀 本番監視スタート")

    while True:
        try:
            bingx_monitor.run()
            person_monitor.run()
            time.sleep(30)
        except Exception as e:
            print("エラー:", e)
            time.sleep(10)


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    # 🔥 これを追加（重要）
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), Handler)
    print(f"🌐 Web server running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    t = threading.Thread(target=monitor_loop)
    t.daemon = True
    t.start()

    start_web_server()
