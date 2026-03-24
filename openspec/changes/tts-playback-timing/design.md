## Context

Twilio Media Streams WebSocket supports three key control messages we're not using:
- **`mark`** (send): attach a named marker after audio chunks. Twilio sends back a `mark` event with the same name when playback reaches that point.
- **`mark`** (receive): confirmation that Twilio played all audio up to the marker.
- **`clear`** (send): immediately flush Twilio's audio buffer, stopping playback.

This is the official Twilio mechanism for playback synchronization — used in their own OpenAI Realtime API reference implementation.

## Goals / Non-Goals

**Goals:**
- Wait for actual playback completion (via mark event) before transitioning SPEAKING → LISTENING
- Clear Twilio's audio buffer on barge-in so the customer doesn't hear stale audio
- No sleep-based timing — mark events are the authoritative signal

**Non-Goals:**
- Sentence-level streaming (sending mark per sentence) — future optimization
- Audio recording — out of scope

## Decisions

### 1. Mark protocol in TwilioTelephonyProvider

Add to `twilio_provider.py`:
- `_mark_futures: dict[str, asyncio.Future]` — pending mark confirmations
- `_mark_counter: int` — unique mark name generator
- `send_mark(call_id) -> None` — sends mark, awaits Twilio's confirmation
- `clear_audio(call_id) -> None` — sends clear to flush buffer
- Update `handle_media_message()` to resolve mark futures on incoming mark events

### 2. Pipeline integration

In `_tts_loop()`:
- After sending all audio chunks, call `await self.telephony.send_mark(call_id)`
- Only then transition to LISTENING

In `_stt_loop()` barge-in:
- Call `await self.telephony.clear_audio(call_id)` to stop playback immediately

### 3. No test needed for mark timing

The mark event is a Twilio server-side feature — we can't test it without a real Twilio connection. The existing Level 2 live call test covers this implicitly. Unit testing would require mocking the entire WebSocket protocol which adds complexity without value.

## Risks / Trade-offs

- **[Risk] Mark event never arrives** → Mitigation: add timeout (5 sec) to mark wait, transition to LISTENING on timeout with a warning log
- **[Trade-off] clear on barge-in may cut off mid-word** → Acceptable — immediate responsiveness is more important than finishing a word
