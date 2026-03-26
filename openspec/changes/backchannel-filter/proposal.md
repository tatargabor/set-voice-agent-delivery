## Why

A voice agent minden hang hatására barge-in-t detektál — az ügyfél "mhm", "igen", "aha" visszajelzéseit is megszakításnak veszi és leáll. Ez természetellenes élményt ad. A backchannel szűrő megkülönbözteti a valódi megszakítást a puszta visszajelzéstől.

## What Changes

- Backchannel szólista a pipeline-ban — magyar "mhm", "igen", "aha", "oké", "értem", stb.
- Szóhossz-alapú szűrő: ≤2 szavas backchannel → agent folytatja; ≤2 szavas stop-szó ("nem", "stop", "várj") → barge-in; 3+ szó → barge-in
- A `_stt_loop` SPEAKING állapotban a barge-in fragment-et először a szűrőn engedi át mielőtt leállítaná az agent-et

## Capabilities

### New Capabilities
- `backchannel-detection`: Szólista + szóhossz-alapú szűrő a barge-in fragmentek klasszifikálására (backchannel vs valódi megszakítás)

### Modified Capabilities

## Impact

- `src/pipeline.py` — `_stt_loop` barge-in kezelése módosul
- Új modul vagy függvény a szűrő logikához
