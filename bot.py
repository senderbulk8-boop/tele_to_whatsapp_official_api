import os
import requests
import json
from datetime import datetime, timedelta

# ==================== Secrets ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
TARGET_NUMBER = "917737781986"   # आपका नंबर

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

def send_text(text):
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
        print(f"📤 Text Status: {r.status_code}")
        if r.status_code != 200:
            print(f"Error: {r.text[:500]}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Text Error: {e}")
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
            print(f"❌ Upload Failed: {upload.text}")
            return False
            
        media_id = upload.json()['id']
        
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
        
        print(f"📤 Media Status: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text[:400])
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Media Error: {e}")
        return False

def main():
    print(f"🚀 Bot Started at {datetime.now()}")
    print(f"Target Number: {TARGET_NUMBER}")

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
        print(f"📥 Found {len(updates)} updates from Telegram")

        for update in updates:
            message = update.get("message")
            if not message:
                continue

            user = message.get("from", {}).get("first_name", "Unknown")
            print(f"📨 Processing message from {user}")

            # Text Message
            if message.get("text"):
                text = f"📨 Telegram से ({user}):\n{message['text']}"
                send_text(text)

