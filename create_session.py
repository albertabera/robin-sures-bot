from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

if not API_ID or not API_HASH:
    print("❌ Please ensure API_ID and API_HASH are in your .env file")
    exit(1)

print("🚀 Telegram Session Generator")
print("------------------------------")
print(f"Using API_ID: {API_ID}")
print("Follow the prompts to log in (Phone number, Code, Password if 2FA).")

with TelegramClient(StringSession(), int(API_ID), API_HASH) as client:
    session_string = client.session.save()
    with open("session.txt", "w") as f:
        f.write(session_string)
        
    print("\n" + "="*50)
    print("✅ NEW SESSION STRING GENERATED AND SAVED TO session.txt")
    print("-" * 20)
    print(session_string)
    print("-" * 20)
    print("Copy this string and replace TELEGRAM_STRING_SESSION in your local .env file")
    print("to use a separate session for the scraper.")
    print("="*50 + "\n")
