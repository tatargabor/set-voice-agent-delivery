"""Persistent inbound call server.

Usage:
    python -m src.inbound_server --port 8765

The server runs continuously, accepting incoming calls on the configured
Twilio phone number. Callers are matched to customers via contacts.yaml.

Setup:
    1. Start ngrok: ngrok http 8765
    2. Configure Twilio number webhook: https://<ngrok-url>/twilio/voice
       (Twilio Console → Phone Numbers → your number → Voice → "A Call Comes In")
    3. Start this server: python -m src.inbound_server
    4. Call your Twilio number from any phone
"""

import argparse
import signal
import structlog
import uvicorn

from .config import validate_config
from . import webhook

log = structlog.get_logger()


def parse_args():
    parser = argparse.ArgumentParser(description="Inbound voice call server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--contacts", default="contacts.yaml", help="Contacts file path")
    return parser.parse_args()


def main():
    args = parse_args()

    # Validate config
    config = validate_config(providers=["anthropic", "soniox", "google_tts", "twilio"])
    log.info("config_loaded")

    # Enable inbound mode
    webhook.enable_inbound_mode()
    log.info("inbound_mode_enabled")

    print("\n=== Inbound Voice Agent Server ===")
    print(f"Listening on port {args.port}")
    print(f"Contacts: {args.contacts}")
    print(f"\nConfigure your Twilio number webhook to:")
    print(f"  https://<your-ngrok-url>/twilio/voice")
    print(f"\nThen call your Twilio number to test.")
    print("Press Ctrl+C to stop.\n")

    # Run uvicorn (blocks until stopped)
    uvicorn.run(webhook.app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
