import os
import requests
import json
from datetime import datetime, timedelta

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

def send_to_whatsapp(text):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "group",
        "to": WHATSAPP_GROUP_ID,
        "type": "text",
        "text": {"body": text[:2000]}   # WhatsApp limit
    }
    try:
        r = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        print(f"📤 Text Send Status: {r.status_code}")
        if r.status_code != 200:
            print(f"Error: {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Text Send Error: {e}")
        return False

def download_file(file_id):
    try:
        get_file = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}")
        file_path = get_file.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        return requests.get(download_url).content
    except Exception as e:
        print(f"❌ Download Failed: {e}")
        return None

def send_media(media_bytes, media_type, caption=""):
    try:
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        files = {'file': ('media', media_bytes, media_type)}
        
        upload = requests.post(f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media", 
                             headers=headers, files=files, timeout=30)
        
        if upload.status_code != 200:
            print(f"❌ Media Upload Failed: {upload.text}")
            return False
            
        media_id = upload.json()['id']
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "group",
            "to": WHATSAPP_GROUP_ID,
        }
        
        if media_type.startswith('image'):
            payload["type"] = "image"
            payload["image"] = {"id": media_id}
        elif media_type.startswith('video'):
            payload["type"] = "video"
            payload["video"] = {"id": media_id}
        else:
            payload["type"] = "document"
            payload["document"] = {"id": media_id}
        
        if caption:
            if "image" in payload:
                payload["image"]["caption"] = caption
            elif "video" in payload:
                payload["video"]["caption"] = caption
            else:
                payload["document"]["caption"] = caption[:200]
        
        resp = requests.post(WHATSAPP_API_URL, json=payload, headers={**headers, "Content-Type": "application/json"}, timeout=15)
        print(f"📤 Media Send Status: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text)
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Media Send Exception: {e}")
        return False

def send_window_reminder():
    reminder = "🔔 Group को Active रखने के लिए Admin के पोस्ट पर text reply कर दो (Emoji काफी नहीं है)"
    send_to_whatsapp(reminder)
    save_last_reminder()

def main():
    print(f"🚀 Bot Started at {datetime.now()}")
    print(f"Phone ID: {PHONE_NUMBER_ID[:8]}...")

    # Reminder
    if datetime.now() - load_last_reminder() > timedelta(hours=20):
        send_window_reminder()

    offset = load_offset()
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 10, "timeout": 10}

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        if not data.get("ok"):
            print("❌ Telegram API Error")
            return

        updates = data.get("result", [])
        print(f"📥 Found {len(updates)} updates")

        for update in updates:
            message = update.get("message")
            if not message:
                continue

            user = message.get("from", {}).get("first_name", "Unknown")
            print(f"📨 New message from {user}")

            # Text
            if message.get("text"):
                text = f"📨 Telegram ({user}):\n{message['text']}"
                send_to_whatsapp(text)

            # Photo
            elif message.get("photo"):
                photo = message["photo"][-1]
                print("🖼️ Image detected, downloading...")
                file_bytes = download_file(photo["file_id"])
                if file_bytes:
                    send_media(file_bytes, "image/jpeg", f"From {user}")

            # Video
            elif message.get("video"):
                video = message["video"]
                print("🎥 Video detected, downloading...")
                file_bytes = download_file(video["file_id"])
                if file_bytes:
                    send_media(file_bytes, "video/mp4", f"From {user}")

            # Document
            elif message.get("document"):
                doc = message["document"]
                print(f"📄 Document detected: {doc.get('file_name')}")
                file_bytes = download_file(doc["file_id"])
                if file_bytes:
                    mime = doc.get("mime_type", "application/pdf")
                    send_media(file_bytes, mime, f"From {user} - {doc.get('file_name','')}")

            offset = update["update_id"] + 1

        save_offset(offset)
        print("✅ Processing Done\n")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()
