from telethon import TelegramClient, events
import requests
import os
import asyncio

# Telegram API
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")

# WhatsApp API
meta_token = os.getenv("META_TOKEN")
phone_id = os.getenv("PHONE_ID")

# Telegram Client
client = TelegramClient("session", api_id, api_hash)

print("Telegram Connected")

# WhatsApp Send Function
def send_whatsapp_message(number, message):

    url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {meta_token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": number,
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(url, headers=headers, json=data)

    print(response.text)

    if response.status_code == 200:
        print("Message Sent Successfully")
    else:
        print("Failed To Send Message")


# Telegram Message Listener
@client.on(events.NewMessage)
async def handler(event):

    msg = event.raw_text

    print("New Telegram Message:")
    print(msg)

    # Yahan apna WhatsApp number likho country code ke sath
    send_whatsapp_message(
        "918104894648",
        msg
    )


async def main():

    await client.start()

    print("Bot Running...")

    await client.run_until_disconnected()


asyncio.run(main())
