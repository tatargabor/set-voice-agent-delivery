## Context

A pipeline `_stt_loop` SPEAKING állapotban bármilyen STT transcript-re barge-in-t triggerel — leállítja a TTS-t és LISTENING-re vált. Ez backchannel-ekre ("mhm") is megtörténik.

## Goals / Non-Goals

**Goals:**
- Backchannel szűrő: ≤2 szavas visszajelzések ne triggereljenek barge-in-t
- Stop-szavak ("nem", "stop", "várj", "de") mindig barge-in
- 3+ szavas megszólalás mindig barge-in
- Nulla extra latencia (szólista lookup, nem API hívás)

**Non-Goals:**
- Speaker diarization (Phase 2)
- ML-alapú interruption detection modell
- Audio-szintű elemzés

## Decisions

### Szűrő a pipeline-ban, nem külön modul
Egyszerű függvény (`is_backchannel(text) -> bool`) közvetlenül a pipeline.py-ban vagy egy kis helper-ben. Nincs szükség külön modulra 20 sornyi kódhoz.

### Magyar szólista
Backchannel: "mhm", "aha", "igen", "ja", "jó", "oké", "értem", "uhum", "rendben", "persze", "naná", "hát", "ühüm", "ööö"
Stop (mindig barge-in): "nem", "stop", "várj", "de", "figyelj", "halló", "hé"

### Normalizálás
STT output-ot lowercase + strip + írásjelek eltávolítása után hasonlítjuk.

## Risks / Trade-offs

- [False negative — valódi megszakítás ignorálva] → Stop-szó lista + 3+ szó mindig barge-in. Az ügyfél legfeljebb meg kell ismételje ha 1 szóval próbált megszakítani ami nincs a stop-listában.
- [False positive — backchannel mégis barge-in lesz] → Csak 1-2 szavas, ismert szavakra szűrünk, minimális kockázat.
