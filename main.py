import os
import requests
import json
from datetime import datetime, timedelta

# ------------------- Secrets -------------------
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_GROUP_ID = os.getenv('WHATSAPP_GROUP_ID')

WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
OFFSET_FILE = "last_offset.json"
LAST_REMINDER_FILE = "last_reminder.json"

def load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, 'r') as f:
                return json.load(f).get("offset", 0)
        except:
            return 0
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, 'w') as f:
        json.dump({"offset": offset}, f)

def load_last_reminder():
    if os.path.exists(LAST_REMINDER_FILE):
        try:
            with open(LAST_REMINDER_FILE, 'r') as f:
                return datetime.fromisoformat(json.load(f).get("time"))
        except:
            return datetime.now() - timedelta(hours=30)
    return datetime.now() - timedelta(hours=30)

def save_last_reminder():
    with open(LAST_REMINDER_FILE, 'w') as f:
        json.dump({"time": datetime.now().isoformat()}, f)

def send_to_whatsapp(message_text: str):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "group",
        "to": WHATSAPP_GROUP_ID,
        "type": "text",
        "text": {"body": message_text}
    }
    
    try:
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            print("✅ Sent successfully")
            return True
        else:
            error = response.json().get('error', {})
            print(f"❌ Error {response.status_code}: {error.get('message')}")
            if "24-hour" in str(error.get('message', '')).lower() or error.get('code') == 131047:
                print("🚨 WINDOW CLOSED - Members को text reply करने को कहो")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def send_window_reminder():
    reminder = """🔔 Group Window Active रखने के लिए:
    
👉 Admin के किसी भी पोस्ट पर सिर्फ Emoji मत दो।
👉 कम से कम 1-2 शब्द लिखकर Reply कर दो जैसे:
"OK", "👍 Received", "Thanks", "Done" आदि

इससे 24 घंटे का window reset हो जाएगा और auto messages free रहेंगे।"""
    
    print("📢 Sending window reminder...")
    send_to_whatsapp(reminder)
    save_last_reminder()

def main():
    offset = load_offset()
    print(f"🔄 [{datetime.now()}] Checking Telegram messages...")
    
    # Reminder logic (हर ~20 घंटे में)
    last_reminder = load_last_reminder()
    if datetime.now() - last_reminder > timedelta(hours=20):
        send_window_reminder()
    
    # Telegram updates check
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 30, "timeout": 10}
    
    try:
        resp = requests.get(url, params=params, timeout=20)
        data = resp.json()
        
        if data.get("ok"):
            updates = data.get("result", [])
            for update in updates:
                if update.get("message") and update["message"].get("text"):
                    msg = update["message"]
                    text = msg["text"]
                    user = msg.get("from", {}).get("first_name", "Unknown")
                    forwarded = f"📨 Telegram ({user}):\n{text}"
                    send_to_whatsapp(forwarded)
                    offset = update["update_id"] + 1
            save_offset(offset)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
