## Why

A jelenlegi pipeline az ügyfél beszéde után ~1200ms-ot vár a Soniox endpoint detection-re, mielőtt bármit küldene a Claude-nak. Ez a teljes válaszidő ~40%-a (3-4 sec-ből). Interim transcript feldolgozással a Claude már a csend-várakozás alatt elkezdhet dolgozni, ~700ms-t faragva a perceived latency-ből.

## What Changes

- Soniox STT provider interim transcript yield-elés: nem csak `<fin>`/`<end>` tokennél, hanem ha elég szó gyűlt össze + rövid csend (~500ms)
- Pipeline `_stt_loop` megkülönbözteti az interim és final transzkripteket
- Pipeline `_llm_loop` spekulatívan elindítja a Claude-ot interim-re, és cancel-el ha a final eltér
- `endpoint_delay_ms` csökkentése 1200ms-ről 800ms-re
- Új config opció: `interim_enabled` és `interim_min_words` / `interim_silence_ms`

## Capabilities

### New Capabilities
- `interim-transcript`: Interim (spekulatív) transcript feldolgozás — STT provider partial yield, pipeline speculative LLM execution, cancel/retry ha a final eltér

### Modified Capabilities

## Impact

- `src/providers/soniox_stt.py` — `transcribe_stream` yield típus változás (str → TranscriptEvent tuple/dataclass)
- `src/providers/base.py` — STTProvider interface bővítés a TranscriptEvent típussal
- `src/pipeline.py` — `_stt_loop` és `_llm_loop` logika módosítás
- `config.yaml` — új interim szekció + endpoint_delay_ms módosítás
- `src/config.py` — új config mezők
