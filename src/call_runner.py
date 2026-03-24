"""CLI entry point for outbound voice calls.

Setup (ngrok for local development):
    1. Install ngrok: https://ngrok.com/download
    2. Start tunnel: ngrok http 8765
    3. Copy the https URL (e.g. https://abc123.ngrok-free.app)

Usage:
    python -m src.call_runner \
        --script website_followup \
        --phone "+36301234567" \
        --customer-name "Kovács János" \
        --company-name "WebBuilder Kft." \
        --website-url "https://kovacs-janos.hu" \
        --public-url "https://abc123.ngrok-free.app"
"""

import argparse
import asyncio
import threading
import time
import structlog
import uvicorn

from .config import validate_config
from .script_loader import load_script
from .safety import CallSafety
from .agent import ConversationAgent
from .pipeline import CallPipeline
from .providers.soniox_stt import SonioxSTTProvider
from .providers.google_tts import GoogleTTSProvider
from .providers.twilio_provider import TwilioTelephonyProvider
from . import webhook

log = structlog.get_logger()

# DNC trigger phrases
DNC_PHRASES = ["ne hívjatok", "ne hívjanak", "ne telefonáljatok", "ne telefonáljanak"]


def parse_args():
    parser = argparse.ArgumentParser(description="Outbound voice call agent")
    parser.add_argument("--script", required=True, help="Call script name (e.g. website_followup)")
    parser.add_argument("--phone", required=True, help="Phone number to call (E.164)")
    parser.add_argument("--customer-name", required=True, help="Customer name")
    parser.add_argument("--company-name", required=True, help="Company name")
    parser.add_argument("--website-url", default=None, help="Website URL (optional)")
    parser.add_argument("--webhook-host", default="0.0.0.0", help="Webhook server host")
    parser.add_argument("--webhook-port", type=int, default=8765, help="Webhook server port")
    parser.add_argument("--public-url", required=True, help="Public URL for Twilio webhooks (e.g. ngrok URL)")
    return parser.parse_args()


def _start_server(host: str, port: int):
    """Start uvicorn in a background thread."""
    config = uvicorn.Config(webhook.app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)  # Wait for server to start
    return server


async def run_call(args):
    """Execute the full outbound call lifecycle."""
    # 1. Load config
    config = validate_config(providers=["anthropic", "soniox", "google_tts", "twilio"])
    log.info("config_loaded")

    # 2. Load script
    variables = {
        "customer_name": args.customer_name,
        "company_name": args.company_name,
    }
    if args.website_url:
        variables["website_url"] = args.website_url
    ctx = load_script(args.script, variables)
    log.info("script_loaded", script=args.script, customer=ctx.customer_name)

    # 3. Safety checks
    safety = CallSafety()
    safety.pre_call_check(args.phone)
    log.info("safety_checks_passed")

    # 4. Initialize providers (STT/TTS connect inside pipeline.run() to stay in the right event loop)
    stt = SonioxSTTProvider()
    tts = GoogleTTSProvider()
    telephony = TwilioTelephonyProvider()
    agent = ConversationAgent()

    try:
        # 5. Build pipeline
        pipeline = CallPipeline(stt=stt, tts=tts, telephony=telephony, agent=agent)

        # 6. Start webhook server
        _start_server(args.webhook_host, args.webhook_port)
        webhook_url = f"{args.public_url}/twilio/voice"
        log.info("webhook_server_started", url=webhook_url)

        # 7. Place call
        call_id = await telephony.place_call(args.phone, webhook_url)
        log.info("call_placed", call_id=call_id, phone=args.phone)

        # 8. Configure webhook with pipeline state
        done_event = asyncio.Event()
        webhook.configure(ctx, pipeline, telephony, call_id, done_event)

        # 9. Wait for call to complete
        await done_event.wait()
        log.info("call_completed")

        # 10. Hangup
        try:
            await telephony.hangup(call_id)
        except Exception:
            pass  # May already be hung up

        # 11. Check for DNC request in transcript
        for msg in ctx.history:
            if msg["role"] == "user":
                text_lower = msg["content"].lower()
                if any(phrase in text_lower for phrase in DNC_PHRASES):
                    safety.add_to_dnc(args.phone)
                    log.info("dnc_request_detected", phone=args.phone)
                    break

        # 12. Print transcript
        print("\n--- Transcript ---")
        for msg in ctx.history:
            role = "Agent" if msg["role"] == "assistant" else "Ügyfél"
            print(f"  {role}: {msg['content']}")
        print(f"\n--- Hívás vége ({len(ctx.history)} üzenet) ---")

    finally:
        pass  # STT/TTS disconnect handled by pipeline.run()


def main():
    args = parse_args()
    asyncio.run(run_call(args))


if __name__ == "__main__":
    main()
