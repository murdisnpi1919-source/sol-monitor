import time
import bingx_monitor
import person_monitor

print("🚀 統合クラウド監視スタート")

while True:
    try:
        bingx_monitor.run()
        person_monitor.run()
        time.sleep(30)
    except Exception as e:
        print("エラー:", e)
        time.sleep(10)