## Context

A jelenlegi kód a system prompt-ot sima string-ként küldi minden API hívásnál. Az Anthropic prompt caching lehetővé teszi, hogy a system prompt (vagy annak egy része) cache-elve legyen a szerveren, így a következő híváskor nem kell újra feldolgozni.

A system prompt két részből áll (`agent.py:_build_system_prompt`):
1. **Statikus rész** (~500 token): base instructions, szabályok — hívás közben nem változik
2. **Project context** (~1000-2000 token): projekt összefoglaló — hívás közben nem változik

Mindkettő cache-elhető, mert egy hívás során nem változnak.

## Goals / Non-Goals

**Goals:**
- Prompt caching minden deep response hívásnál (streaming, tool_use)
- Greeting prompt caching
- Cache usage tracking a metricsben
- Minimális kód módosítás — `cache_control` paraméter hozzáadása

**Non-Goals:**
- Fast ack (Haiku) caching — túl rövid prompt (<100 token), a Haiku minimum 4096 token
- Conversation history caching — a history minden turn-nél változik
- Custom TTL konfiguráció — 5 perces default elég voice call-hoz

## Decisions

### 1. Top-level cache_control paraméter használata

Az Anthropic SDK két módot támogat:
- **Top-level**: `cache_control={"type": "ephemeral"}` — egyszerű, az egész system prompt-ot cache-eli
- **Explicit blocks**: system prompt list of dicts `cache_control` mezővel — finomabb kontroll

**Döntés: top-level**, mert:
- 1 sor módosítás API hívásonként
- A system prompt teljes egészében statikus egy hívás alatt
- Nem kell a prompt struktúrát módosítani

```python
# Előtte:
await self.client.messages.stream(
    model=self.deep_model,
    system=system_prompt,
    messages=ctx.history,
    max_tokens=300,
)

# Utána:
await self.client.messages.stream(
    model=self.deep_model,
    system=system_prompt,
    messages=ctx.history,
    max_tokens=300,
    cache_control={"type": "ephemeral"},
)
```

### 2. Csak deep model és greeting kap caching-et

| Hívás | Modell | System prompt | Cache? |
|---|---|---|---|
| Fast ack | Haiku | ~100 token | NEM — Haiku min 4096 token |
| Deep stream | Sonnet | ~2500 token | IGEN — Sonnet min 1024 token |
| Deep tool_use | Sonnet | ~2500 token | IGEN |
| Local agent | Sonnet | ~2500 token | IGEN |
| Greeting | Sonnet | ~200 token | NEM — túl rövid |

A greeting system prompt (~200 token) túl rövid a caching-hez, de a deep response prompt (base + project context) bőven felette van.

### 3. Cache usage tracking

Az Anthropic response `usage` objektuma tartalmazza:
- `cache_read_input_tokens` — cache hit-ből olvasott tokenek
- `cache_creation_input_tokens` — újonnan cache-elt tokenek

Ezeket a `CallMetrics`-ben trackeljük az input/output tokenek mellé.

## Risks / Trade-offs

**[Cache write 1.25× drágább]** → Mitigáció: egy 6 turn-ös hívásban 1 write + 5 read = 1.25 + 5×0.1 = 1.75× költség összesen, szemben 6× = 6.0× caching nélkül. Megtakarítás: 71%.

**[Cache TTL 5 perc]** → Mitigáció: egy tipikus hívás 1-3 perc, bőven belefér. Ha az ügyfél visszahív 5 percen belül, az is cache hit.

**[Minimum token korlát]** → Mitigáció: a system prompt project context-tel ~2500 token, Sonnet minimum 1024 — bőven felette.
