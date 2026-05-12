import os
import json
import requests
from telethon.sync import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")

META_TOKEN = os.getenv("META_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")

WHATSAPP_NUMBER = "918104894648"

CHANNEL = "RAJASTHAN_TODAY"

client = TelegramClient("session", API_ID, API_HASH)

if not os.path.exists("sent_messages.json"):
    with open("sent_messages.json", "w") as f:
        json.dump([], f)

with open("sent_messages.json", "r") as f:
    sent = json.load(f)

client.start()

messages = client.get_messages(CHANNEL, limit=1)

msg = messages[0]

if str(msg.id) in sent:
    print("Already Sent")
    quit()

caption = msg.text if msg.text else "hello its positron academy testing"

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
        "body": caption
    }
}

response = requests.post(url, headers=headers, json=data)

print(response.text)

sent.append(str(msg.id))

with open("sent_messages.json", "w") as f:
    json.dump(sent, f)
