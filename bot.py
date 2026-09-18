import os
import json
import requests
import re
from datetime import datetime

# ====================== CONFIG ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# Sender: 8104894648 (WHATSAPP_PHONE_NUMBER_ID secret)
# Receiver: 7737781986
RECEIVER = "917737781986"

TEMPLATE_NAME = (os.getenv("WHATSAPP_TEMPLATE_NAME") or "").strip()
TEMPLATE_LANG = os.getenv("WHATSAPP_TEMPLATE_LANG") or "en"

LAST_OFFSET = 826690574  # Code khud update karega
# ====================================================

GRAPH = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}"
WHATSAPP_API_URL = f"{GRAPH}/messages"
REPLACEMENT_USERNAME = "@KapilRJ06"

# positronacademy.in links (http/https/www/subdomain) filter se bahar
PA_LINK_RE = re.compile(
    r"(https?://(?:www\.)?(?:[A-Za-z0-9-]+\.)*positronacademy\.in(?:[^\s]*)?)"
    r"|(?:(?<=\s)|^)(?:www\.)?positronacademy\.in(?:/[^\s]*)?",
    re.I,
)

WA_HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json",
}


def clean_text(text):
    """@mentions replace, lekin positronacademy.in links bilkul mat chhedo."""
    if not text:
        return text

    saved = []

    def _park(match):
        saved.append(match.group(0))
        return f"@@PA{len(saved) - 1}@@"

    protected = PA_LINK_RE.sub(_park, text)
    protected = re.sub(r"@\w+", REPLACEMENT_USERNAME, protected)
    for i, url in enumerate(saved):
        protected = protected.replace(f"@@PA{i}@@", url)
    return protected


def has_positron_link(text):
    return bool(text and PA_LINK_RE.search(text))


def update_offset_in_file(new_offset):
    try:
        with open(__file__, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(r"LAST_OFFSET = \d+", f"LAST_OFFSET = {new_offset}", content)
        with open(__file__, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ Offset auto-updated to {new_offset}")
    except Exception as e:
        print(f"⚠️ Offset file update failed: {e}")


def explain_wa_error(code, body):
    print(f"❌ WhatsApp error {code}: {body[:800]}")
    if code == 131047:
        print(
            "   24-hour window band hai.\n"
            "   7737781986 wale phone se WhatsApp pe 8104894648 ko Hi bhejo.\n"
            "   Uske baad 24 ghante messages jayenge."
        )
    elif code == 131030:
        print(
            "   Number allow-list me nahi.\n"
            "   Meta Dashboard → WhatsApp → API Setup → To me 917737781986 add + OTP verify."
        )
    elif code == 131026:
        print("   Number WhatsApp pe nahi / undeliverable. 917737781986 check karo.")
    elif code in (190, 0, 10):
        print("   Token/permission problem. WHATSAPP_TOKEN naya generate karo.")
    elif code == 131021:
        print("   Sender aur receiver same number hai.")


def post_message(payload):
    r = requests.post(WHATSAPP_API_URL, json=payload, headers=WA_HEADERS, timeout=20)
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text}
    print(f"   WA HTTP {r.status_code}: {json.dumps(data)[:800]}")
    return r.status_code, data


def send_template(to, text):
    if not TEMPLATE_NAME:
        return False
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": (text or "update")[:1024]}],
                }
            ],
        },
    }
    print(f"🔁 24h window — template '{TEMPLATE_NAME}' se bhej rahe hain...")
    status, data = post_message(payload)
    if status == 200:
        return True
    err = data.get("error") or {}
    explain_wa_error(err.get("code"), json.dumps(data))
    return False


def send_text(text):
    body = (text or "").strip()[:4096]
    if not body:
        print("ℹ️ Empty text, skip")
        return True
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": RECEIVER,
        "type": "text",
        "text": {
            "preview_url": has_positron_link(body),
            "body": body,
        },
    }
    print(f"📨 Text → {RECEIVER}")
    status, data = post_message(payload)
    if status == 200:
        return True
    err = data.get("error") or {}
    code = err.get("code")
    if code == 131047:
        return send_template(RECEIVER, body)
    explain_wa_error(code, json.dumps(data))
    return False


def upload_media(file_bytes, mime, filename):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    files = {
        "file": (filename, file_bytes, mime),
        "messaging_product": (None, "whatsapp"),
        "type": (None, mime),
    }
    upload = requests.post(f"{GRAPH}/media", headers=headers, files=files, timeout=60)
    print(f"   Media upload HTTP {upload.status_code}: {upload.text[:400]}")
    if upload.status_code != 200:
        return None
    return upload.json().get("id")


def send_media(file_bytes, mime, caption="", filename="file.bin"):
    print(f"📸 Media ({mime}) → {RECEIVER}")
    media_id = upload_media(file_bytes, mime, filename)
    if not media_id:
        if caption:
            return send_text(caption)
        return False

    if mime.startswith("image"):
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": RECEIVER,
            "type": "image",
            "image": {"id": media_id},
        }
        if caption:
            payload["image"]["caption"] = caption[:1024]
    elif mime.startswith("video"):
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": RECEIVER,
            "type": "video",
            "video": {"id": media_id},
        }
        if caption:
            payload["video"]["caption"] = caption[:1024]
    elif mime.startswith("audio"):
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": RECEIVER,
            "type": "audio",
            "audio": {"id": media_id},
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": RECEIVER,
            "type": "document",
            "document": {"id": media_id, "filename": filename},
        }
        if caption:
            payload["document"]["caption"] = caption[:1024]

    status, data = post_message(payload)
    if status == 200:
        return True
    err = data.get("error") or {}
    code = err.get("code")
    if code == 131047:
        return send_template(RECEIVER, caption or "media")
    explain_wa_error(code, json.dumps(data))
    return False


def download_file(file_id):
    try:
        meta = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}",
            timeout=15,
        )
        info = meta.json()
        if not info.get("ok"):
            print(f"❌ Telegram getFile failed: {info}")
            return None
        file_path = info["result"]["file_path"]
        raw = requests.get(
            f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}",
            timeout=60,
        )
        if raw.status_code != 200:
            print(f"❌ Telegram file download HTTP {raw.status_code}")
            return None
        return raw.content
    except Exception as e:
        print(f"❌ Telegram download error: {e}")
        return None


def forward_message(message):
    original_caption = clean_text(message.get("caption") or "").strip()

    if message.get("text"):
        return send_text(clean_text(message["text"]))

    if message.get("photo"):
        print("🖼️ Image")
        photo = message["photo"][-1]
        file_bytes = download_file(photo["file_id"])
        if not file_bytes:
            return False
        return send_media(file_bytes, "image/jpeg", original_caption, "photo.jpg")

    if message.get("video") or message.get("animation"):
        print("🎬 Video")
        media = message.get("video") or message.get("animation")
        file_bytes = download_file(media["file_id"])
        if not file_bytes:
            return False
        mime = media.get("mime_type") or "video/mp4"
        return send_media(file_bytes, mime, original_caption, "video.mp4")

    if message.get("document"):
        doc = message["document"]
        print(f"📄 Document: {doc.get('file_name')}")
        file_bytes = download_file(doc["file_id"])
        if not file_bytes:
            return False
        mime = doc.get("mime_type") or "application/octet-stream"
        name = doc.get("file_name") or "file.bin"
        return send_media(file_bytes, mime, original_caption, name)

    if message.get("voice") or message.get("audio"):
        print("🎵 Audio")
        media = message.get("voice") or message.get("audio")
        file_bytes = download_file(media["file_id"])
        if not file_bytes:
            return False
        mime = media.get("mime_type") or "audio/ogg"
        ok = send_media(file_bytes, mime, original_caption, "audio.ogg")
        if not ok and original_caption:
            return send_text(original_caption)
        return ok

    if message.get("sticker"):
        print("🏷️ Sticker")
        sticker = message["sticker"]
        file_bytes = download_file(sticker["file_id"])
        if not file_bytes:
            return False
        mime = "image/webp" if not sticker.get("is_animated") else "video/mp4"
        name = "sticker.webp" if mime == "image/webp" else "sticker.mp4"
        return send_media(file_bytes, mime, original_caption, name)

    return True


def main():
    print(f"\n🚀 Bot Started - {datetime.now()}")
    print("📌 Sender business: 8104894648 (via PHONE_NUMBER_ID)")
    print(f"📌 Receiver: {RECEIVER}")

    missing = [
        n
        for n, v in (
            ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
            ("WHATSAPP_TOKEN", WHATSAPP_TOKEN),
            ("WHATSAPP_PHONE_NUMBER_ID", PHONE_NUMBER_ID),
        )
        if not v
    ]
    if missing:
        print(f"❌ Missing GitHub secrets: {', '.join(missing)}")
        return

    current_offset = LAST_OFFSET
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"offset": current_offset, "limit": 20, "timeout": 10},
            timeout=20,
        )
        payload = resp.json()
        if not payload.get("ok"):
            print(f"❌ Telegram getUpdates failed: {payload}")
            return

        updates = payload.get("result") or []
        if not updates:
            print("ℹ️ No new messages")
            return

        failed = False
        for update in updates:
            update_id = update["update_id"]
            if update_id < current_offset:
                continue

            message = update.get("message") or update.get("channel_post")
            if not message:
                current_offset = update_id + 1
                continue

            ok = forward_message(message)
            if not ok:
                print(
                    f"❌ Forward failed for Telegram update_id={update_id} — "
                    "offset yahin rukega, next run retry karega"
                )
                failed = True
                break

            current_offset = update_id + 1

        if current_offset > LAST_OFFSET:
            update_offset_in_file(current_offset)

        if failed:
            print("❌ WhatsApp send fail. 7737781986 se 8104894648 ko Hi bhejo, phir workflow dubara chalao.")
            return

        print(f"✅ Forwarded to {RECEIVER}")
    except Exception as e:
        print(f"❌ Error: {e}")
        if current_offset > LAST_OFFSET:
            update_offset_in_file(current_offset)


if __name__ == "__main__":
    main()
