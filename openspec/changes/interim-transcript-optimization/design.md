## Context

A voice pipeline jelenleg úgy működik, hogy a Soniox STT provider csak `<fin>`/`<end>` token esetén yield-el transzkriptet (`soniox_stt.py:71-73`). Ez azt jelenti, hogy a `max_endpoint_delay_ms` (1200ms) teljes egészében "halott idő" — a Claude tétlenül vár amíg a Soniox megbizonyosodik róla, hogy az ügyfél befejezte a mondatot.

A pipeline 3 async loop-ból áll (`pipeline.py`): `_stt_loop` → `_stt_queue` → `_llm_loop` → `_tts_queue` → `_tts_loop`. A queue jelenleg sima `str`-eket szállít.

## Goals / Non-Goals

**Goals:**
- Az endpoint detection alatti halott idő kihasználása: Claude spekulatívan elindul az interim transzkriptre
- ~700ms latency csökkentés a tipikus esetben (interim = final)
- Graceful fallback: ha az interim nem egyezik a final-lal, cancel + újraindítás
- Config-ból ki/bekapcsolható

**Non-Goals:**
- TTS provider váltás (az egy külön change)
- Google TTS streaming API (külön change)
- Prompt caching (Anthropic feature, ortogonális)
- Speculative response (LLM elindul mielőtt a user befejezte) — túl kockázatos

## Decisions

### 1. TranscriptEvent dataclass a raw str helyett

A `transcribe_stream` visszatérési típusa `str`-ről `TranscriptEvent`-re változik:

```python
@dataclass
class TranscriptEvent:
    text: str
    is_interim: bool  # True = spekulatív, False = végleges
```

**Miért nem tuple?** Dataclass egyértelmű, bővíthető (pl. confidence score később), és a pipeline kód olvashatóbb.

**Backwards compatibility:** A `STTProvider` ABC `transcribe_stream` visszatérési típusa `AsyncIterator[str]`-ről `AsyncIterator[TranscriptEvent]`-re változik. Ez breaking change, de csak egy implementáció van (Soniox), és a pipeline az egyetlen consumer.

### 2. Interim detection logika a Soniox provider-ben

Az interim yield feltétele:
- Legalább `interim_min_words` szó gyűlt össze (default: 3)
- Legalább `interim_silence_ms` ms telt el az utolsó token óta (default: 500)
- Még nem kaptunk `<fin>`/`<end>` tokent

A Soniox event loop-ban egy timestamp-et tartunk az utolsó token érkezéséről. Ha a csend meghaladja a küszöböt ÉS elég szó van, yield-elünk egy interim event-et.

**Probléma:** A Soniox event loop blocking — `async for event in session.receive_events()` vár a következő event-re, tehát nincs természetes "tick" a csend-detektálásra.

**Megoldás:** `asyncio.wait_for` timeout-tal a receive loop-ban. Ha timeout (interim_silence_ms), és van elég szó, yield interim. Ha nem timeout (új token jött), accumulate és reset timer.

```
async for event in session:     ← jelenlegi, blocking
↓
while True:                     ← új, timeout-os
    try:
        event = await asyncio.wait_for(
            session.__anext__(), timeout=interim_silence_ms/1000
        )
        # process tokens, reset silence timer
    except asyncio.TimeoutError:
        # silence detected — yield interim if enough words
```

### 3. Pipeline spekulatív LLM indítás

A `_stt_queue` `TranscriptEvent`-eket szállít. A `_llm_loop` logikája:

```
interim event → elindít egy asyncio.Task-ot a response_layers.respond()-del
              → tárolja a task referenciát + interim szöveget

final event   → ha final.text == interim.text:
                  nincs teendő, a task már fut/kész
              → ha final.text != interim.text:
                  cancel task, újraindít final szöveggel

(ha nincs interim, csak final → ugyanaz mint ma)
```

**Miért nem a response_layers-ben?** A spekuláció a pipeline szintű orchestráció dolga, nem a response layer-é. A response_layers.respond() nem tud arról, hogy spekulatív-e — ez szándékos separation of concerns.

### 4. Cancel mechanizmus

A `response_layers.respond()` egy `AsyncGenerator` — cancel-lése egyszerű: `task.cancel()`. De a TTS queue-ra már kerülhetett fast ack szöveg az interim alapján.

**Megoldás:** Ha cancel, a pipeline:
1. Cancel-li a deep response task-ot
2. Beállítja a `_tts_cancel_event`-et (már létezik, barge-in-hez)
3. Üríti a `_tts_queue`-t
4. Újraindítja a respond()-et a final szöveggel

A fast ack (ha már elhangzott) nem baj — az egy rövid nyugtázás volt, nem tartalmaz érdemi választ.

### 5. Config bővítés

```yaml
voice:
  endpoint_delay_ms: 800          # csökkentve 1200-ról
  interim_enabled: true
  interim_min_words: 3
  interim_silence_ms: 500
```

## Risks / Trade-offs

**[Dupla API cost ha interim téves]** → Mitigáció: a `interim_min_words: 3` és `interim_silence_ms: 500` kombinációja a legtöbb esetben kiszűri a false positive-ot. Magyar beszédben az 500ms+ szünet mondat közepén ritka. Worst case: egy extra Haiku fast ack (kb. $0.0001).

**[STT provider interface breaking change]** → Mitigáció: csak egy implementáció van, és a pipeline az egyetlen consumer. Nincs external dependency.

**[Komplexebb pipeline state management]** → Mitigáció: a spekulatív task egyetlen `asyncio.Task` referencia + egy string összehasonlítás. Nem kell state machine bővítés.

**[Timeout-os receive loop megváltoztatja a Soniox streaming viselkedést]** → Mitigáció: ha `interim_enabled: false`, a régi logika fut változatlanul. Feature flag mögött van.

## Open Questions

- A Soniox `receive_events()` támogatja-e az `__anext__()` hívást közvetlenül (async iterator protocol), vagy wrapper kell? Implementáció során kiderül.
- Kell-e confidence threshold az interim-hez? (pl. csak akkor yield, ha a Soniox token confidence > 0.8) — egyelőre nem, egyszerűség.
