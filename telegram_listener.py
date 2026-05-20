import requests
import os
import time
import datetime
from screener import main as run_scan

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

COMMANDS = ["/scan", "/run", "/check"]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    })

def get_recent_updates():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    r = requests.get(url, params={"limit": 20}, timeout=10)
    return r.json().get("result", [])

def main():
    updates = get_recent_updates()
    now = int(time.time())
    six_minutes_ago = now - 360  # 6 min window covers the 5-min poll gap

    for update in updates:
        msg = update.get("message", {})
        text = msg.get("text", "").strip().lower()
        chat_id = str(msg.get("chat", {}).get("id", ""))
        msg_time = msg.get("date", 0)

        # Only respond to YOUR chat, recent messages, valid commands
        if chat_id != CHAT_ID:
            continue
        if msg_time < six_minutes_ago:
            continue
        if text not in COMMANDS:
            continue

        # Command found — run the scan
        send_telegram("⚡ *Command received! Starting scan now...*")
        run_scan()
        return

    print("No commands found in last 6 minutes.")

if __name__ == "__main__":
    main()
