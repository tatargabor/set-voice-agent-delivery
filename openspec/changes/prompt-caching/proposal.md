## Why

A voice agent minden turn-nél elküldi a teljes system prompt-ot (~2000-3000 token: base instructions + project context) a Claude API-nak. Egy 6 turn-ös hívásban ez 6× feldolgozás ugyanarra a promptra. Az Anthropic prompt caching API-val a system prompt cache-elhető: az első hívásnál 1.25× költség, utána 0.1× (90% megtakarítás) és ~3.3× gyorsabb first-token latency a cache hit-eknél.

## What Changes

- System prompt cache_control breakpoint hozzáadása minden Claude API hívásnál (streaming, tool_use, agent)
- A system prompt felépítése explicit cache block struktúrával: statikus rész (cache-elhető) + dinamikus rész (nem cache-elt)
- Cache usage tracking a metrics-ben (cache_read_input_tokens, cache_creation_input_tokens)
- Greeting is használjon prompt caching-et

## Capabilities

### New Capabilities
- `prompt-cache-integration`: Anthropic prompt caching integráció — cache_control breakpoint a system prompt-on, cache usage tracking, explicit static/dynamic prompt szeparáció

### Modified Capabilities

## Impact

- `src/response_layers.py` — cache_control paraméter minden Claude API hívásnál
- `src/agent.py` — system prompt építés block struktúrával, greeting caching
- `src/metrics.py` — cache hit/miss tracking
- Költség: ~90% input token megtakarítás a 2+ turn-ös hívásoknál
- Latency: ~3.3× gyorsabb first-token a cache hit-eknél
