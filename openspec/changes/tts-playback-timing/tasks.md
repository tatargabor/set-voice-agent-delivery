## 1. Twilio Provider — mark/clear support

- [x] 1.1 Add `_mark_futures: dict[str, asyncio.Future]` and `_mark_counter: int` to `TwilioTelephonyProvider`
- [x] 1.2 Implement `send_mark(call_id)` — send mark event, await Twilio confirmation with 5s timeout
- [x] 1.3 Implement `clear_audio(call_id)` — send clear event to flush Twilio's buffer
- [x] 1.4 Update `handle_media_message()` to resolve mark futures on incoming mark events

## 2. Pipeline — await mark before state transition

- [x] 2.1 In `_tts_loop()`: after sending all audio chunks, call `await self.telephony.send_mark(call_id)` before transitioning to LISTENING
- [x] 2.2 In `_stt_loop()` barge-in: call `await self.telephony.clear_audio(call_id)` before transitioning to LISTENING
- [x] 2.3 In greeting: await mark after sending greeting audio before transitioning to LISTENING
