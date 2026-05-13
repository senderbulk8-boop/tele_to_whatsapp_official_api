import os
import requests
import re
from datetime import datetime

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')

# === SMART TARGET HANDLING ===
targets_str = os.getenv("WHATSAPP_TARGETS", "") or os.getenv("WHATSAPP_GROUP_ID", "")
TARGETS = [t.strip() for t in targets_str.split(",") if t.strip()]

# === USERNAME REPLACE ===
REPLACEMENT_USERNAME = "@KapilRJ06"
# ============================

LAST_OFFSET = 0
WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

def clean_caption(caption):
    if not caption:
        return ""
    # @username ya @KapilRJ06 wagairah ko replace karo
    return re.sub(r'@[a-zA-Z0-9_]+', REPLACEMENT_USERNAME, caption)

def update_offset_in_file(new_offset):
    try:
        with open(__file__, 'r') as f:
            content = f.read()
        new_content = re.sub(r'LAST_OFFSET = \d+', f'LAST_OFFSET = {new_offset}', content)
        with open(__file__, 'w') as f:
            f.write(new_content)
        print(f"✅ Offset auto-updated to {new_offset}")
    except Exception as e:
        print(f"⚠️ Offset update failed: {e}")

def download_file(file_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15)
        file_path = r.json()['result']['file_path']
        return requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}", timeout=30).content
    except:
        return None

def send_to_target(target, payload):
    if not target:
        return
    try:
        payload["to"] = target
        if "@g.us" in target:
            payload["recipient_type"] = "group"
        else:
            payload["recipient_type"] = "individual"

        r = requests.post(WHATSAPP_API_URL, json=payload,
                         headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
                         timeout=10)
        
        if r.status_code == 200:
            print(f"✅ SUCCESS → {target}")
        else:
            print(f"❌ FAILED → {target} | {r.status_code} | {r.text[:120]}")
    except Exception as e:
        print(f"❌ EXCEPTION → {target} | {str(e)[:80]}")

def send_text(text):
    print(f"\n📨 TEXT → {len(TARGETS)} targets")
    for target in TARGETS:
        payload = {"messaging_product": "whatsapp", "type": "text", "text": {"body": text[:2000]}}
        send_to_target(target, payload)

def send_media(file_bytes, media_type, caption=""):
    print(f"\n📎 MEDIA → {len(TARGETS)} targets")
    clean_cap = clean_caption(caption)
    for target in TARGETS:
        if not target: continue
        try:
            headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
            files = {'file': ('media', file_bytes, media_type), 'messaging_product': (None, 'whatsapp')}
            upload = requests.post(f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media", headers=headers, files=files, timeout=40)
            if upload.status_code != 200:
                print(f"❌ Upload failed for {target}")
                continue
            media_id = upload.json().get('id')
            
            payload = {"messaging_product": "whatsapp"}
            if media_type.startswith('image'):
                payload.update({"type": "image", "image": {"id": media_id, "caption": clean_cap}})
            else:
                payload.update({"type": "document", "document": {"id": media_id, "caption": clean_cap}})
            
            send_to_target(target, payload)
        except Exception as e:
            print(f"❌ Media Error → {target} | {str(e)[:80]}")

def main():
    print(f"\n{'='*65}")
    print(f"🚀 Bot Started - {datetime.now()}")
    print(f"📌 Offset: {LAST_OFFSET}")
    print(f"🎯 Total Targets: {len(TARGETS)}")
    if TARGETS:
        print(f"📋 Targets: {TARGETS}")
    print(f"{'='*65}\n")
    
    current_offset = LAST_OFFSET
    try:
        updates = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={current_offset}&limit=20&timeout=10", timeout=15).json().get("result", [])
        if not updates:
            print("ℹ️ No new messages")
            return
            
        for update in updates:
            update_id = update["update_id"]
            if update_id < current_offset: continue
            message = update.get("message") or update.get("channel_post")
            if not message:
                current_offset = update_id + 1
                continue
                
            user = message.get("from", {}).get("first_name", "Channel")
            caption = message.get("caption") or ""
            
            if message.get("text"):
                send_text(f"📨 Telegram ({user}):\n{message['text']}")
            elif message.get("photo"):
                print("🖼️ Image Detected")
                fb = download_file(message["photo"][-1]["file_id"])
                if fb:
                    send_media(fb, "image/jpeg", caption or f"📨 From Telegram ({user})")
            elif message.get("document"):
                doc = message["document"]
                print(f"📄 Document: {doc.get('file_name')}")
                fb = download_file(doc["file_id"])
                if fb:
                    send_media(fb, doc.get("mime_type", "application/pdf"), caption or f"📨 From Telegram ({user})")
            
            current_offset = update_id + 1
            
        if current_offset > LAST_OFFSET:
            update_offset_in_file(current_offset)
            
        print(f"\n{'='*65}")
        print(f"✅ All done! Next offset: {current_offset}")
        print(f"{'='*65}\n")
        
    except Exception as e:
        print(f"❌ MAIN ERROR: {e}")

if __name__ == "__main__":
    main()
