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
    print(f"🔄 Trying to send to WhatsApp: {text[:100]}...")
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
        print(f"📤 WhatsApp API Response: {r.status_code}")
        if r.status_code == 200:
            print("✅ SUCCESS: Message Sent to Your WhatsApp Number!")
        else:
            print(f"❌ FAILED: {r.text[:500]}")
    except Exception as e:
        print(f"❌ Exception while sending: {e}")

def main():
    print(f"\n🚀 Bot Started at {datetime.now()}")
    print(f"Target Number: {TARGET_NUMBER}")
    print(f"Phone Number ID: {PHONE_NUMBER_ID[:8]}...")

    offset = load_offset()
    print(f"Current Offset: {offset}")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 20, "timeout": 10}

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        print(f"Telegram API Status: {'✅ OK' if data.get('ok') else '❌ Failed'}")
        updates = data.get("result", [])
        print(f"Total Updates Found: {len(updates)}")

        processed = 0
        for update in updates:
            update_id = update.get("update_id")
            message = update.get("message") or update.get("channel_post")
            
            print(f"\n--- Update ID: {update_id} ---")
            
            if not message:
                print("No message or channel_post found in this update")
                offset = update_id + 1
                continue

            user = message.get("from", {}).get("first_name", "Unknown")
            chat_type = message.get("chat", {}).get("type", "unknown")
            print(f"From: {user} | Chat Type: {chat_type}")

            # Text Message
            if message.get("text"):
                text = message["text"]
                print(f"📝 TEXT Found: {text[:100]}")
                forwarded = f"📨 Telegram ({user}):\n{text}"
                send_to_whatsapp(forwarded)
                processed += 1

            # Other types
            elif message.get("photo"):
                print("🖼️ Photo Found")
            elif message.get("video"):
                print("🎥 Video Found")
            elif message.get("document"):
                print("📄 Document Found")
            else:
                print("Other message type (sticker, voice, etc.)")

            offset = update_id + 1

        save_offset(offset)
        print(f"\n✅ Cycle Finished | Processed Messages: {processed} | New Offset: {offset}\n")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()
