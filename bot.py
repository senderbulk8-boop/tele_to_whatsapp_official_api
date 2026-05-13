import os
import requests
import json
import re
from datetime import datetime

# ====================== CONFIG ======================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
TARGET_NUMBER = "917737781986"

# Yeh line code khud update karega - haath mat lagana!
LAST_OFFSET = 826689150
# ====================================================

WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

def update_offset_in_file(new_offset):
    """Code khud hi LAST_OFFSET update karega"""
    try:
        with open(__file__, 'r') as f:
            content = f.read()
        
        new_content = re.sub(
            r'LAST_OFFSET = \d+',
            f'LAST_OFFSET = {new_offset}',
            content
        )
        
        with open(__file__, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Offset auto-updated to {new_offset}")
    except Exception as e:
        print(f"⚠️ Could not auto-update offset: {e}")

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
    except Exception as e:
        print(f"Text Error: {e}")

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
                payload["image"]["caption"] = caption[:1024]
        else:
            payload["type"] = "document"
            payload["document"] = {"id": media_id}
            if caption:
                payload["document"]["caption"] = caption[:1024]
        
        resp = requests.post(WHATSAPP_API_URL, json=payload,
                           headers={**headers, "Content-Type": "application/json"}, timeout=15)
       
        if resp.status_code == 200:
            print("✅ Media Sent with Original Caption")
        else:
            print(f"❌ Send Failed: {resp.status_code}")
           
    except Exception as e:
        print(f"❌ Media Error: {e}")

def main():
    print(f"\n🚀 Bot Started - {datetime.now()}")
    print(f"📌 Starting from Offset: {LAST_OFFSET}")
   
    current_offset = LAST_OFFSET
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": current_offset, "limit": 20, "timeout": 10}
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        updates = resp.json().get("result", [])
        
        if not updates:
            print("ℹ️ No new messages")
            return
            
        for update in updates:
            update_id = update["update_id"]
            
            if update_id < current_offset:
                print(f"⏭️ Skipping old update {update_id}")
                continue
                
            message = update.get("message") or update.get("channel_post")
            if not message:
                current_offset = update_id + 1
                continue
                
            user = message.get("from", {}).get("first_name", "Channel")
            original_caption = message.get("caption") or ""
            
            if message.get("text"):
                forwarded = f"📨 Telegram ({user}):\n{message['text']}"
                send_text(forwarded)
                
            elif message.get("photo"):
                print("🖼️ Image Detected")
                photo = message["photo"][-1]
                file_bytes = download_file(photo["file_id"])
                if file_bytes:
                    caption = original_caption if original_caption else f"📨 From Telegram ({user})"
                    send_media(file_bytes, "image/jpeg", caption)
                    
            elif message.get("document"):
                doc = message["document"]
                print(f"📄 Document: {doc.get('file_name')}")
                file_bytes = download_file(doc["file_id"])
                if file_bytes:
                    mime = doc.get("mime_type", "application/octet-stream")
                    file_name = doc.get('file_name', 'document.pdf')
                    caption = original_caption if original_caption else f"📨 From Telegram ({user})\n📎 {file_name}"
                    send_media(file_bytes, mime, caption)
            
            current_offset = update_id + 1
            
        if current_offset > LAST_OFFSET:
            update_offset_in_file(current_offset)
            
        print(f"\n✅ All done! Next run will start from offset {current_offset}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
