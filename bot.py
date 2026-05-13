import os
import requests
import json
from datetime import datetime

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
TARGET_NUMBER = "917737781986"

WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

OFFSET_FILE = "last_offset.json"

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

def send_to_whatsapp(text):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": TARGET_NUMBER,
        "type": "text",
        "text": {"body": text[:2000]}
    }
    try:
        r = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        print(f"📤 WhatsApp Status: {r.status_code}")
        if r.status_code != 200:
            print(f"Error: {r.text[:300]}")
        else:
            print("✅ Message Sent Successfully to WhatsApp!")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Send Error: {e}")
        return False

def main():
    print(f"🚀 Bot Started - {datetime.now()}")
    
    offset = load_offset()
    print(f"Current Offset: {offset}")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 20, "timeout": 10}

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        updates = data.get("result", [])
        print(f"📥 Found {len(updates)} updates")

        processed = 0
        for update in updates:
            message = update.get("message")
            if not message:
                continue

            user = message.get("from", {}).get("first_name", "Unknown")
            update_id = update["update_id"]
            
            print(f"📨 New Message from {user} (Update ID: {update_id})")

            if message.get("text"):
                text = f"📨 Telegram ({user}):\n{message['text']}"
                send_to_whatsapp(text)
                processed += 1

            # Photo, Video, Document support (basic)
            elif message.get("photo") or message.get("video") or message.get("document"):
                print("🖼️ Media detected (Text forward only for now)")

            # Update offset
            offset = update_id + 1

        save_offset(offset)
        print(f"✅ Done! Processed {processed} messages | New Offset: {offset}\n")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()
