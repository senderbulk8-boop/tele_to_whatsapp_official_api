import os
import requests
import re
from datetime import datetime

# ====================== CONFIG ======================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')

# ←←← SAB TARGETS YAHAN HAIN (Personal + Groups)
TARGETS = [
    "917737781986", # Personal Number
]

LAST_OFFSET = 826689608  # Code khud update karega
# ====================================================

WHATSAPP_API_URL = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"

# ====================== NEW: Username Replacement ======================
REPLACEMENT_USERNAME = "@KapilRJ06"

def replace_usernames(text):
    if not text:
        return text
    return re.sub(r"@\w+", REPLACEMENT_USERNAME, text)
# =====================================================================

def update_offset_in_file(new_offset):
    try:
        with open(__file__, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = re.sub(r'LAST_OFFSET = \d+', f'LAST_OFFSET = {new_offset}', content)
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ Offset auto-updated to {new_offset}")
    except:
        pass

def download_file(file_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15)
        file_path = r.json()['result']['file_path']
        return requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}", timeout=30).content
    except:
        return None

def send_to_target(target, payload):
    try:
        r = requests.post(WHATSAPP_API_URL, json=payload, headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }, timeout=12)
        status = "✅ Sent" if r.status_code == 200 else f"❌ Failed {r.status_code}"
        print(f" → {target[:12]}... {status}")
    except Exception as e:
        print(f" → {target[:12]}... Error: {e}")

def send_text(text):
    print(f"📨 Sending Text to {len(TARGETS)} targets...")
    for target in TARGETS:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "group" if "@g.us" in target else "individual",
            "to": target,
            "type": "text",
            "text": {"body": text[:2000]}
        }
        send_to_target(target, payload)

def send_media(file_bytes, media_type, caption=""):
    print(f"📸 Sending Media to {len(TARGETS)} targets...")
    try:
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        files = {'file': ('media', file_bytes, media_type), 'messaging_product': (None, 'whatsapp')}
       
        upload = requests.post(f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/media",
                             headers=headers, files=files, timeout=40)
       
        if upload.status_code != 200:
            print(f"❌ Media Upload Failed: {upload.text[:300]}")
            return
       
        media_id = upload.json().get('id')
       
        for target in TARGETS:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "group" if "@g.us" in target else "individual",
                "to": target,
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
           
            send_to_target(target, payload)
           
    except Exception as e:
        print(f"❌ Media Error: {e}")

def main():
    print(f"\n🚀 Bot Started - {datetime.now()}")
    print(f"📌 Targets: {len(TARGETS)} (1 Personal + Groups)")
  
    current_offset = LAST_OFFSET
    try:
        updates = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={current_offset}&limit=20&timeout=10",
            timeout=15
        ).json().get("result", [])
       
        if not updates:
            print("ℹ️ No new messages")
            return
           
        for update in updates:
            update_id = update["update_id"]
            if update_id < current_offset:
                continue
               
            message = update.get("message") or update.get("channel_post")
            if not message:
                current_offset = update_id + 1
                continue
               
            user = message.get("from", {}).get("first_name", "Channel")
            original_caption = message.get("caption") or ""
           
            if message.get("text"):
                original_text = message['text']
                updated_text = replace_usernames(original_text)          # ← NEW
                forwarded = f"📨 Telegram ({user}):\n{updated_text}"
                send_text(forwarded)
               
            elif message.get("photo"):
                print("🖼️ Image Detected")
                photo = message["photo"][-1]
                file_bytes = download_file(photo["file_id"])
                if file_bytes:
                    if original_caption:
                        caption = replace_usernames(original_caption)     # ← NEW
                    else:
                        caption = f"📨 From Telegram ({user})"
                    send_media(file_bytes, "image/jpeg", caption)
                   
            elif message.get("document"):
                doc = message["document"]
                print(f"📄 Document: {doc.get('file_name')}")
                file_bytes = download_file(doc["file_id"])
                if file_bytes:
                    mime = doc.get("mime_type", "application/octet-stream")
                    if original_caption:
                        caption = replace_usernames(original_caption)     # ← NEW
                    else:
                        caption = f"📨 From Telegram ({user})\n📎 {doc.get('file_name','Document')}"
                    send_media(file_bytes, mime, caption)
           
            current_offset = update_id + 1
           
        if current_offset > LAST_OFFSET:
            update_offset_in_file(current_offset)
           
        print(f"✅ All messages forwarded to {len(TARGETS)} targets!")
       
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
