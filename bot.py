import os
import requests
import re
from datetime import datetime

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')

# === TARGETS (Personal + Business + 5 Main Groups) ===
TARGETS = [
    "917737781986",                    # Personal Number
   
]

REPLACEMENT_USERNAME = "@KapilRJ06"
LAST_OFFSET = 826689167
WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

def clean_caption(caption):
    if not caption: return ""
    return re.sub(r'@[a-zA-Z0-9_]+', REPLACEMENT_USERNAME, caption)

def update_offset_in_file(new_offset):
    try:
        with open(__file__, 'r') as f: content = f.read()
        new_content = re.sub(r'LAST_OFFSET = \d+', f'LAST_OFFSET = {new_offset}', content)
        with open(__file__, 'w') as f: f.write(new_content)
        print(f"✅ Offset updated to {new_offset}")
    except: pass

def download_file(file_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}", timeout=15)
        return requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{r.json()['result']['file_path']}", timeout=30).content
    except: return None

def send_to_target(target, payload):
    try:
        payload["to"] = target
        payload["recipient_type"] = "group" if "@g.us" in target else "individual"
        
        r = requests.post(WHATSAPP_API_URL, json=payload,
                         headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
                         timeout=10)
        if r.status_code == 200:
            print(f"✅ SUCCESS → {target}")
        else:
            print(f"❌ FAILED → {target} | {r.status_code} | {r.text[:100]}")
    except Exception as e:
        print(f"❌ ERROR → {target} | {str(e)[:60]}")

def send_text(text):
    print(f"\n📨 TEXT to {len(TARGETS)} targets...")
    for t in TARGETS:
        send_to_target(t, {"messaging_product": "whatsapp", "type": "text", "text": {"body": text[:2000]}})

def send_media(file_bytes, media_type, caption=""):
    print(f"\n📎 MEDIA to {len(TARGETS)} targets...")
    clean_cap = clean_caption(caption)
    for t in TARGETS:
        try:
            headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
            files = {'file': ('media', file_bytes, media_type), 'messaging_product': (None, 'whatsapp')}
            upload = requests.post(f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media", headers=headers, files=files, timeout=40)
            if upload.status_code != 200: continue
            mid = upload.json().get('id')
            payload = {"messaging_product": "whatsapp"}
            if media_type.startswith('image'):
                payload.update({"type": "image", "image": {"id": mid, "caption": clean_cap}})
            else:
                payload.update({"type": "document", "document": {"id": mid, "caption": clean_cap}})
            send_to_target(t, payload)
        except Exception as e:
            print(f"❌ Media error {t}")

def main():
    print(f"\n{'='*65}\n🚀 Bot Started | Targets: {len(TARGETS)} | Offset: {LAST_OFFSET}\n{'='*65}")
    current = LAST_OFFSET
    try:
        updates = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={current}&limit=20", timeout=15).json().get("result", [])
        if not updates:
            print("ℹ️ No new messages")
            return
        for u in updates:
            mid = u["update_id"]
            if mid < current: continue
            msg = u.get("message") or u.get("channel_post")
            if not msg:
                current = mid + 1
                continue
            user = msg.get("from", {}).get("first_name", "User")
            cap = msg.get("caption") or ""
            if msg.get("text"):
                send_text(f"📨 Telegram ({user}):\n{msg['text']}")
            elif msg.get("photo"):
                fb = download_file(msg["photo"][-1]["file_id"])
                if fb: send_media(fb, "image/jpeg", cap or f"From Telegram ({user})")
            elif msg.get("document"):
                fb = download_file(msg["document"]["file_id"])
                if fb: send_media(fb, msg["document"].get("mime_type", "application/pdf"), cap or f"From Telegram ({user})")
            current = mid + 1
        if current > LAST_OFFSET:
            update_offset_in_file(current)
        print(f"\n✅ Done! Next offset: {current}\n{'='*65}")
    except Exception as e:
        print(f"❌ Main Error: {e}")

if __name__ == "__main__":
    main()
