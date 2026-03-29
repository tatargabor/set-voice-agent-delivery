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
from datetime import datetime

from .config import validate_config
from .script_loader import load_script
from .safety import CallSafety
from .agent import ConversationAgent
from .metrics import CallMetrics, mask_phone, calculate_costs
from .logger import CallLogger
from .pipeline import CallPipeline
from .response_layers import ResponseLayers
from .providers.soniox_stt import SonioxSTTProvider
from .providers.google_tts import GoogleTTSProvider
from .providers.twilio_provider import TwilioTelephonyProvider
from . import webhook

log = structlog.get_logger()

# DNC trigger phrases
from .i18n import _DNC_PHRASES, _TRANSCRIPT_LABELS, get_text

DNC_PHRASES = get_text(_DNC_PHRASES)


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

    # 4. Initialize providers
    stt = SonioxSTTProvider()
    tts = GoogleTTSProvider()
    telephony = TwilioTelephonyProvider()
    agent = ConversationAgent()

    outcome = "error"  # default, updated on success

    try:
        # 5. Create metrics
        metrics = CallMetrics(
            call_id="pending",
            timestamp_start=datetime.now(),
            customer_name=args.customer_name,
            script_name=args.script,
            phone_masked=mask_phone(args.phone),
        )

        # 6. Build pipeline with metrics + dual-layer response
        pipeline = CallPipeline(stt=stt, tts=tts, telephony=telephony, agent=agent, metrics=metrics)
        pipeline.response_layers = ResponseLayers()

        # 7. Start webhook server
        _start_server(args.webhook_host, args.webhook_port)
        webhook_url = f"{args.public_url}/twilio/voice"
        log.info("webhook_server_started", url=webhook_url)

        # 8. Place call
        call_id = await telephony.place_call(args.phone, webhook_url)
        metrics.call_id = call_id
        log.info("call_placed", call_id=call_id, phone=args.phone)

        # 9. Configure webhook with pipeline state
        done_event = threading.Event()
        webhook.configure(ctx, pipeline, telephony, call_id, done_event)

        # 10. Wait for call to complete (threading.Event because webhook runs in uvicorn thread)
        await asyncio.get_event_loop().run_in_executor(None, done_event.wait)
        log.info("call_completed")
        outcome = "completed"

        # 11. Hangup
        try:
            await telephony.hangup(call_id)
        except Exception:
            pass  # May already be hung up

        # 12. Check for DNC request in transcript
        for msg in ctx.history:
            if msg["role"] == "user":
                text_lower = msg["content"].lower()
                if any(phrase in text_lower for phrase in DNC_PHRASES):
                    safety.add_to_dnc(args.phone)
                    log.info("dnc_request_detected", phone=args.phone)
                    outcome = "dnc"
                    break

        # 13. Fetch Twilio call price
        try:
            call_details = telephony._client.calls(call_id).fetch()
            if call_details.price:
                metrics.twilio_price = float(call_details.price)
            if call_details.duration:
                metrics.twilio_duration_sec = int(call_details.duration)
        except Exception as e:
            log.warning("twilio_price_fetch_failed", error=str(e))

        # 14. Save call log
        call_logger = CallLogger()
        filepath = call_logger.save(metrics, ctx.history, outcome=outcome)
        log.info("call_logged", path=str(filepath))

        # 15. Print transcript
        print("\n--- Transcript ---")
        for msg in ctx.history:
            labels = get_text(_TRANSCRIPT_LABELS)
            role = labels["agent"] if msg["role"] == "assistant" else labels["customer"]
            print(f"  {role}: {msg['content']}")

        # 16. Print cost summary
        labels = get_text(_TRANSCRIPT_LABELS)
        costs = calculate_costs(metrics)
        print(f"\n--- {labels['cost']} ---")
        print(f"  Twilio:     ${costs['twilio']:.4f}")
        print(f"  Claude:     ${costs['claude']:.4f}")
        print(f"  Google TTS: ${costs['google_tts']:.6f}")
        print(f"  Soniox STT: ${costs['soniox_stt']:.6f}")
        print(f"  {labels['total']}:   ${costs['total']:.4f}")
        print(f"\n--- {labels['call_end']} ({len(ctx.history)} msg, log: {filepath.name}) ---")

    finally:
        pass  # STT/TTS disconnect handled by pipeline.run()


def main():
    args = parse_args()
    asyncio.run(run_call(args))


if __name__ == "__main__":
    main()
