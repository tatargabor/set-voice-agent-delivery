## Why

The agent transitions to LISTENING as soon as TTS audio chunks are **sent** to Twilio — not when Twilio **finishes playing** them. This causes the agent and customer to talk over each other: the agent starts listening for a response while Twilio is still playing the previous reply. In testing, the agent asked the same question 3 times because it picked up its own unfinished audio as customer speech.

## What Changes

- Add Twilio Media Streams `mark` event support: after sending all TTS audio, send a `mark` message and wait for Twilio's `mark` callback confirming playback completion before transitioning to LISTENING
- Add Twilio `clear` event support for barge-in: when customer interrupts, send `clear` to immediately flush Twilio's audio buffer (currently we only stop sending, but buffered audio keeps playing)
- Update pipeline to await mark confirmation before state transitions

## Capabilities

### New Capabilities
- `twilio-mark-sync`: Use Twilio mark/clear events to synchronize TTS playback with pipeline state transitions

### Modified Capabilities

## Impact

- **Code**: modify `src/providers/twilio_provider.py` (add send_mark, clear_audio, handle mark events), modify `src/pipeline.py` (await mark after TTS, clear on barge-in)
- **No new dependencies**
- **No API changes** — uses existing Twilio Media Streams WebSocket protocol features
