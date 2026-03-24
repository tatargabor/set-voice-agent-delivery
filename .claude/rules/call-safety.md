# Call Safety Rules

## Legal
- NEVER place calls outside legal hours (08:00-20:00 local time)
- ALWAYS inform the customer that the call may be recorded (GDPR)
- Maintain and check Do Not Call (DNC) list before every call
- Provide opt-out mechanism: if customer says "ne hívjatok", add to DNC

## Security
- Phone numbers MUST come from environment or database, never hardcoded in source
- API keys (Soniox, Twilio, Anthropic) MUST be in environment variables
- PII in transcripts MUST be masked before logging (phone numbers, addresses)
- Call recordings MUST be stored encrypted with retention policy

## Error Handling
- If STT fails mid-call: apologize and offer callback
- If Claude fails mid-call: use fallback script (pre-recorded responses)
- If telephony drops: log the event, do NOT auto-redial immediately
- Rate limit: max 1 call per customer per day
