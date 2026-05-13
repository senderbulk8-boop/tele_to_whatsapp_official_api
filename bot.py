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
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}")
        file_path = r.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        return requests.get(download_url).content
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
        print(f"📤 Text: {r.status_code}")
        return r.status_code == 200
    except:
        return False

def send_media(file_bytes, media_type, caption=""):
    try:
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        files = {'file': ('media', file_bytes, media_type)}
        
        # Upload media
        upload = requests.post(f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media", 
                             headers=headers, files=files, timeout=30)
        
        if upload.status_code != 200:
            print(f"❌ Media Upload Failed: {upload.text[:200]}")
            return False

        media_id = upload.json()['id']

        # Send media
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
        elif media_type.startswith('video'):
            payload["type"] = "video"
            payload["video"] = {"id": media_id}
            if caption:
                payload["video"]["caption"] = caption
        else:
            payload["type"] = "document"
            payload["document"] = {"id": media_id}
            if caption:
                payload["document"]["caption"] = caption[:200]

        resp = requests.post(WHATSAPP_API_URL, json=payload, 
                           headers={**headers, "Content-Type": "application/json"}, timeout=15)
        
        print(f"📤 Media Sent: {resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Media Error: {e}")
        return False

def main():
    print(f"\n🚀 Bot Started - {datetime.now()}")
    
    offset = load_offset()
    print(f"Current Offset: {offset}")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 15, "timeout": 10}

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        updates = data.get("result", [])
        print(f"📥 Total Updates: {len(updates)}")

        processed = 0
        for update in updates:
            message = update.get("message")
            if not message:
                continue

            user = message.get("from", {}).get("first_name", "Unknown")
            update_id = update["update_id"]

            print(f"\n📨 From: {user} | Update ID: {update_id}")

            # Text
            if message.get("text"):
                forwarded = f"📨 Telegram ({user}):\n{message['text']}"
                send_text(forwarded)
                processed += 1

            # Image
            elif message.get("photo"):
                print("🖼️ Image Detected")
                photo = message["photo"][-1]
                file_bytes = download_file(photo["file_id"])
                if file_bytes:
                    caption = f"From Telegram ({user})"
                    send_media(file_bytes, "image/jpeg", caption)
                    processed += 1

            # Video
            elif message.get("video"):
                print("🎥 Video Detected")
                video = message["video"]
                file_bytes = download_file(video["file_id"])
                if file_bytes:
                    caption = f"From Telegram ({user})"
                    send_media(file_bytes, "video/mp4", caption)
                    processed += 1

            # Document / PDF
            elif message.get("document"):
                doc = message["document"]
                print(f"📄 Document: {doc.get('file_name')}")
                file_bytes = download_file(doc["file_id"])
                if file_bytes:
                    mime = doc.get("mime_type", "application/pdf")
                    caption = f"From: {user} | {doc.get('file_name','')}"
                    send_media(file_bytes, mime, caption)
                    processed += 1

            offset = update_id + 1

        save_offset(offset)
        print(f"\n✅ Cycle Completed | Processed: {processed} items\n")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
