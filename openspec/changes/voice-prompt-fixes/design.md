## Context

Claude responds with markdown formatting that TTS reads literally. Outbound greeting is wrong direction.

## Goals / Non-Goals

**Goals:**
- Plain spoken Hungarian in all Claude responses (no `**`, `#`, emoji)
- Outbound greeting explains purpose of our call
- Inbound greeting unchanged

**Non-Goals:**
- Changing response content/quality
- Adding new TTS features

## Decisions

### 1. System prompt additions
Add to `_build_system_prompt()` in `agent.py`:
- "A válaszod telefonon lesz felolvasva TTS-sel. NE használj markdown formázást, csillagokat, hasheket, emojikat, kódot. Tiszta beszélt magyar nyelven válaszolj."

### 2. Fast ack prompt
Update `_fast_ack()` system prompt in `response_layers.py` — same rule.

### 3. Outbound vs inbound greeting
Add `call_direction` field to `CallContext` (`inbound` | `outbound`). The greeting in `agent.py` changes based on direction:
- `inbound`: "Jó napot, a {company} ügyfélszolgálata, miben segíthetek?"
- `outbound`: "Jó napot, a {company}-tól hívom, {purpose}"
