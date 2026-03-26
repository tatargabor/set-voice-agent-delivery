## Context

A voice agent hívás közben a `project_context.py` nyers fájlokat olvas és csonkolja őket. Az agent így csak töredékes képet kap a projektről. A cél: projekt kiválasztáskor egy Claude-dal generált összefoglaló készüljön előre, amit a hívás indulásakor a system prompt-ba töltünk.

Jelenlegi flow:
```
Widget → projekt kiválaszt → hívás indul → project_context.py nyers betöltés (csonkolt)
```

Új flow:
```
Widget → projekt kiválaszt → POST /api/index-project → Claude Haiku összefoglal → cache
                                                                                     ↓
                              hívás indul → project_context.py cache-ből tölt ← ─ ─ ┘
```

## Goals / Non-Goals

**Goals:**
- Widget-ben projekt kiválasztáskor Claude Haiku összefoglalja a projekt teljes docs/ és openspec/ tartalmát
- Cache-elt összefoglaló, ami mtime-alapon invalidálódik
- A hívás indulásakor az összefoglaló kerül a system prompt-ba a nyers fájlok helyett
- Az összefoglaló strukturált: modulok, design, állapot, korábbi kérések

**Non-Goals:**
- Forráskód indexelése (az marad tool call-ra)
- Valós idejű frissítés hívás közben
- Több projekt egyidejű indexelése

## Decisions

### 1. Haiku a summarizáláshoz, nem Sonnet/Opus
Az indexelés háttérben fut, nem kell a legokosabb modell. Haiku gyors (~500ms) és olcsó. Az összefoglaló struktúrája fix prompt-tal vezérelt, nem kell kreatív gondolkodás.

### 2. Fájl-alapú cache (`logs/indexes/<project_id>.json`)
Egyszerű, nem kell adatbázis. A JSON tartalmazza az összefoglalót + a forrás fájlok mtime-jait. Ha bármelyik fájl módosult, újragenerálódik.

### 3. Async endpoint, nem blocking
A `/api/index-project` azonnal válaszol `{"status": "indexing"}`, a háttérben fut az indexelés. A widget polling-gal vagy egyszerű timeout-tal várja meg. Ha a hívás előbb indul mint az index kész, fallback a nyers betöltésre.

### 4. Összefoglaló struktúra fix prompt-tal
```
Projekt neve: ...
Leírás: ...
Modulok/Oldalak: ...
Design (színek, font, stílus): ...
Állapot (kész/folyamatban/tervezett): ...
Korábbi ügyfélkérések: ...
```
Ez biztosítja hogy az összefoglaló konzisztens és az agent tudja mire számítson.

## Risks / Trade-offs

- [Haiku hallucináció] → A fix struktúrájú prompt minimalizálja. Az összefoglaló mellé a tool-ok továbbra is elérhetők ha az ügyfél pontos részletet kér.
- [Cache elavulás] → mtime ellenőrzés minden hívás előtt. Ha a fejlesztő push-ol, a következő hívásra frissül.
- [Index endpoint nem kész mire hívás indul] → Fallback: a jelenlegi nyers betöltés fut, az agent így is működik, csak kevesebb kontextussal.
