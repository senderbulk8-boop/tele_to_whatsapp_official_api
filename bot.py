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

def download_telegram_file(file_id):
    """Telegram से file download करके bytes return करे"""
    try:
        # Get file path
        file_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        file_path = requests.get(file_url).json()['result']['file_path']
        
        # Download file
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        response = requests.get(download_url)
        return response.content
    except:
        return None

def send_media_to_whatsapp(media_bytes, media_type, caption=""):
    """WhatsApp पर media भेजना"""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    # Media upload करें
    files = {'file': ('media', media_bytes, media_type)}
    upload_url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media"
    
    try:
        upload_resp = requests.post(upload_url, headers=headers, files=files)
        if upload_resp.status_code != 200:
            print("❌ Media Upload Failed:", upload_resp.text)
            return False
        
        media_id = upload_resp.json()['id']
        
        # Final message send
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "group",
            "to": WHATSAPP_GROUP_ID,
            "type": media_type.split('/')[0] if '/' in media_type else "document",
        }
        
        if media_type.startswith('image'):
            payload["image"] = {"id": media_id}
        elif media_type.startswith('video'):
            payload["video"] = {"id": media_id}
        else:
            payload["document"] = {"id": media_id}
        
        if caption:
            if media_type.startswith('image') or media_type.startswith('video'):
                payload["image" if media_type.startswith('image') else "video"]["caption"] = caption
            else:
                payload["document"]["caption"] = caption
        
        resp = requests.post(WHATSAPP_API_URL, json=payload, headers={**headers, "Content-Type": "application/json"})
        
        if resp.status_code == 200:
            print(f"✅ {media_type} sent successfully")
            return True
        else:
            print(f"❌ Media Send Failed: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Media Error: {e}")
        return False

def send_to_whatsapp(text=""):
    if not text:
        return False
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "group",
        "to": WHATSAPP_GROUP_ID,
        "type": "text",
        "text": {"body": text}
    }
    try:
        r = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
        return r.status_code == 200
    except:
        return False

def send_window_reminder():
    reminder = """🔔 Group Window Active रखने के लिए:
👉 Admin के पोस्ट पर सिर्फ Emoji मत दो
👉 कम से कम "OK", "Received", "Thanks" जैसा text reply जरूर कर दो"""
    send_to_whatsapp(reminder)
    save_last_reminder()

def main():
    offset = load_offset()
    print(f"🔄 [{datetime.now()}] Checking new messages from Telegram...")
    
    # Reminder
    if datetime.now() - load_last_reminder() > timedelta(hours=20):
        send_window_reminder()
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 15, "timeout": 10}
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if not data.get("ok"):
            return
            
        for update in data.get("result", []):
            msg = update.get("message")
            if not msg:
                continue
                
            user = msg.get("from", {}).get("first_name", "Unknown")
            caption = msg.get("caption", "")
            forwarded_caption = f"📨 Telegram ({user}):\n{caption}" if caption else f"📨 From Telegram ({user})"
            
            # Text Message
            if msg.get("text"):
                text = f"📨 Telegram ({user}):\n{msg['text']}"
                send_to_whatsapp(text)
                
            # Photo
            elif msg.get("photo"):
                photo = msg["photo"][-1]  # highest quality
                file_bytes = download_telegram_file(photo["file_id"])
                if file_bytes:
                    send_media_to_whatsapp(file_bytes, "image/jpeg", forwarded_caption)
                    
            # Video
            elif msg.get("video"):
                video = msg["video"]
                file_bytes = download_telegram_file(video["file_id"])
                if file_bytes:
                    send_media_to_whatsapp(file_bytes, "video/mp4", forwarded_caption)
                    
            # Document (PDF, etc.)
            elif msg.get("document"):
                doc = msg["document"]
                file_bytes = download_telegram_file(doc["file_id"])
                if file_bytes:
                    mime_type = doc.get("mime_type", "application/octet-stream")
                    send_media_to_whatsapp(file_bytes, mime_type, forwarded_caption)
            
            offset = update["update_id"] + 1
            
        save_offset(offset)
        
    except Exception as e:
        print(f"❌ Main Error: {e}")

if __name__ == "__main__":
    main()
