import os
import json
import asyncio
import requests

from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

# =========================
# TELEGRAM CONFIG
# =========================

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")

CHANNEL = "RAJASTHAN_TODAY"

# =========================
# WHATSAPP CONFIG
# =========================

META_TOKEN = os.getenv("META_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")

WHATSAPP_NUMBER = "918104894648"

# =========================
# DUPLICATE FILTER FILE
# =========================

SENT_FILE = "sent_messages.json"

if not os.path.exists(SENT_FILE):
    with open(SENT_FILE, "w") as f:
        json.dump([], f)

with open(SENT_FILE, "r") as f:
    sent_messages = json.load(f)

# =========================
# TELEGRAM CLIENT
# =========================

client = TelegramClient(
    "session",
    API_ID,
    API_HASH
)

# =========================
# SEND TEXT TO WHATSAPP
# =========================

def send_whatsapp_text(message):

    url = f"https://graph.facebook.com/v22.0/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": WHATSAPP_NUMBER,
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    print("Status Code:", response.status_code)
print("Response:", response.text)

# =========================
# MAIN FUNCTION
# =========================

async def main():

    await client.connect()

    print("Telegram Connected")

    messages = await client.get_messages(
        CHANNEL,
        limit=1
    )

    if not messages:
        print("No Messages Found")
        return

    msg = messages[0]

    message_id = str(msg.id)

    # DUPLICATE CHECK

    if message_id in sent_messages:
        print("Already Sent")
        return

    # TEXT

    text = msg.text

    if not text:
        text = "hello its positron academy testing"

    # SEND TO WHATSAPP

    send_whatsapp_text(text)

    # SAVE MESSAGE ID

    sent_messages.append(message_id)

    with open(SENT_FILE, "w") as f:
        json.dump(sent_messages, f)

   if response.status_code == 200:
    print("Message Sent Successfully")
else:
    print("Failed To Send")

# =========================
# RUN
# =========================

asyncio.run(main())
