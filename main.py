import threading
import time
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import bingx_monitor
import person_monitor


def monitor_loop():
    print("🚀 監視スタート")

    # 🔥 起動確認テスト通知（3トピック）
    try:
        import requests

        bot = os.getenv("BOT_TOKEN")
        chat = os.getenv("CHAT_ID")

        # 🔴 優先監視
        requests.post(
            f"https://api.telegram.org/bot{bot}/sendMessage",
            json={
                "chat_id": chat,
                "message_thread_id": 5197,
                "text": "🔴 優先監視トピック テスト成功",
            }
        )

        # 📡 ワイド監視
        requests.post(
            f"https://api.telegram.org/bot{bot}/sendMessage",
            json={
                "chat_id": chat,
                "message_thread_id": 5238,
                "text": "📡 ワイド監視トピック テスト成功",
            }
        )

        # 👤 既存ウォレット監視
        requests.post(
            f"https://api.telegram.org/bot{bot}/sendMessage",
            json={
                "chat_id": chat,
                "message_thread_id": 5272,
                "text": "👤 既存ウォレット監視トピック テスト成功",
            }
        )

        print("✅ 全トピックテスト通知送信完了")

    except Exception as e:
        print("テスト通知失敗:", e)

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
