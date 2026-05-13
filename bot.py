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

def download_file(file_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15)
        file_path = r.json()['result']['file_path']
        return requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}", timeout=30).content
    except:
        return None

def send_text(text):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": TARGET_NUMBER,
        "type": "text",
        "text": {"body": text[:2000]}
    }
    try:
        r = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            print("✅ Text Sent")
    except:
        pass

def send_media(file_bytes, media_type, caption=""):
    try:
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        files = {
            'file': ('media', file_bytes, media_type),
            'messaging_product': (None, 'whatsapp')
        }
        
        upload = requests.post(f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media", 
                             headers=headers, files=files, timeout=40)
        
        if upload.status_code != 200:
            print(f"❌ Upload Failed: {upload.text[:200]}")
            return

        media_id = upload.json().get('id')

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": TARGET_NUMBER,
        }

        if media_type.startswith('image'):
            payload["type"] = "image"
            payload["image"] = {"id": media_id}
            if caption:
                payload["image"]["caption"] = caption
        else:  # document / pdf
            payload["type"] = "document"
            payload["document"] = {"id": media_id}
            if caption:
                payload["document"]["caption"] = caption

        resp = requests.post(WHATSAPP_API_URL, json=payload, 
                           headers={**headers, "Content-Type": "application/json"}, timeout=15)
        
        if resp.status_code == 200:
            print("✅ Media Sent with Caption")
        else:
            print(f"Final Send Status: {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Media Error: {e}")

def main():
    print(f"\n🚀 Bot Started - {datetime.now()}")
    
    offset = load_offset()

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 20, "timeout": 10}

    try:
        resp = requests.get(url, params=params, timeout=15)
        updates = resp.json().get("result", [])

        for update in updates:
            message = update.get("message") or update.get("channel_post")
            if not message:
                continue

            update_id = update["update_id"]
            user = message.get("from", {}).get("first_name", "Channel")

            if message.get("text"):
                forwarded = f"📨 Telegram ({user}):\n{message['text']}"
                send_text(forwarded)

            elif message.get("photo"):
                print("🖼️ Image Detected")
                photo = message["photo"][-1]
                file_bytes = download_file(photo["file_id"])
                if file_bytes:
                    send_media(file_bytes, "image/jpeg", f"📨 From Telegram ({user})")

            elif message.get("document"):
                doc = message["document"]
                print(f"📄 Document: {doc.get('file_name')}")
                file_bytes = download_file(doc["file_id"])
                if file_bytes:
                    mime = doc.get("mime_type", "application/pdf")
                    caption = f"📨 From Telegram ({user})\n📎 {doc.get('file_name','Document')}"
                    send_media(file_bytes, mime, caption)

            offset = update_id + 1

        save_offset(offset)
        print("✅ Cycle Completed\n")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
