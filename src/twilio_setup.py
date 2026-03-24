"""One-time Twilio setup for browser voice client.

Creates a TwiML App and API Key. Run once, then add the output to .env.

Usage:
    python -m src.twilio_setup --webhook-url https://<ngrok-url>/twilio/voice
"""

import argparse
import os
from dotenv import load_dotenv
from twilio.rest import Client


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Setup Twilio for browser voice client")
    parser.add_argument("--webhook-url", required=True, help="Public webhook URL (e.g. ngrok)")
    args = parser.parse_args()

    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])

    # 1. Create TwiML App
    twiml_app = client.applications.create(
        friendly_name="Voice Agent Browser Client",
        voice_url=args.webhook_url,
        voice_method="POST",
    )
    print(f"✓ TwiML App created: {twiml_app.sid}")

    # 2. Create API Key
    api_key = client.new_keys.create(friendly_name="Voice Agent Browser Key")
    print(f"✓ API Key created: {api_key.sid}")

    # 3. Output env vars
    print(f"\nAdd these to your .env:\n")
    print(f"TWILIO_API_KEY_SID={api_key.sid}")
    print(f"TWILIO_API_KEY_SECRET={api_key.secret}")
    print(f"TWILIO_TWIML_APP_SID={twiml_app.sid}")


if __name__ == "__main__":
    main()
