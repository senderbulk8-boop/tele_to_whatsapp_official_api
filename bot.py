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
        if r.status_code == 200:
            print("✅ Sent Successfully!")
        else:
            print(f"❌ Error: {r.text[:300]}")
    except Exception as e:
        print(f"❌ Send Error: {e}")

def main():
    print(f"\n🚀 Bot Started - {datetime.now()}")
    
    offset = load_offset()
    print(f"Starting Offset: {offset}")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {
        "offset": offset,
        "limit": 20,
        "timeout": 10,
        "allowed_updates": ["message"]
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        print(f"Telegram Response OK: {data.get('ok')}")

        updates = data.get("result", [])
        print(f"Total Updates Received: {len(updates)}")

        processed = 0
        max_update_id = offset

        for update in updates:
            update_id = update.get("update_id")
            message = update.get("message")

            if not message:
                max_update_id = update_id
                continue

            user = message.get("from", {}).get("first_name", "Unknown")
            print(f"\n📨 Update {update_id} | From: {user}")

            if message.get("text"):
                text = message["text"]
                print(f"📝 Text: {text[:80]}...")
                forwarded = f"📨 Telegram ({user}):\n{text}"
                send_to_whatsapp(forwarded)
                processed += 1

            elif message.get("photo"):
                print("🖼️ Photo received (Media support coming soon)")
            elif message.get("document"):
                print("📄 Document received")

            if update_id > max_update_id:
                max_update_id = update_id

        # Offset Update
        new_offset = max_update_id + 1 if max_update_id > offset else offset
        save_offset(new_offset)
        print(f"\n✅ Cycle Done | Processed: {processed} | New Offset: {new_offset}\n")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()
