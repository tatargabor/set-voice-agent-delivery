## 1. Caller Lookup

- [x] 1.1 Create `contacts.yaml` with sample entries and default section
- [x] 1.2 Create `src/caller_lookup.py` — `lookup_caller(phone)` loads contacts.yaml (hot reload), returns customer data or default
- [x] 1.3 Add test: known number → returns customer data
- [x] 1.4 Add test: unknown number → returns default

## 2. Inbound Webhook

- [x] 2.1 Modify `src/webhook.py` — create pipeline per incoming call inside the POST handler (not from global state)
- [x] 2.2 Extract caller phone from Twilio POST form data (`From` field)
- [x] 2.3 Build CallContext from caller lookup result
- [x] 2.4 Add busy check — if a call is active, return TwiML with "foglalt" message
- [x] 2.5 Add test: POST /twilio/voice with From field → TwiML response

## 3. Inbound Server

- [x] 3.1 Create `src/inbound_server.py` — persistent uvicorn server with CLI args (--port, --contacts)
- [x] 3.2 Configure Twilio number webhook URL on startup (via API or print instructions)
- [x] 3.3 Wire metrics + logging (same as outbound)
- [x] 3.4 Add graceful shutdown on SIGINT/SIGTERM

## 4. Integration

- [ ] 4.1 Add `.env.example` note about inbound mode
- [ ] 4.2 Test: start inbound server, call the Twilio number, verify pipeline runs
