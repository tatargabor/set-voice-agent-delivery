## Why

A voice agent hívás közben a projekt kontextust nyers fájlokból tölti be, csonkolva (spec-enként 800 kar, docs fájlonként 1000 kar). Emiatt az agent nem érti a teljes projektet — fontos részletek elvesznek, és tool call-okkal kell menet közben keresgélnie, ami lassítja a hívást. Egy előre elkészített, Claude-dal összefoglalt projekt index megoldja ezt: a hívás indulásakor az agent már érti a projektet.

## What Changes

- Új API endpoint: `POST /api/index-project` — a widget triggereli projekt kiválasztáskor
- Új modul `src/project_indexer.py` — beolvassa a teljes docs/ és openspec/ tartalmát, Claude Haiku-val összefoglaltatja, és cache-eli
- Cache: `logs/indexes/<project_id>.json` — tartalmazza az összefoglalót + timestamp-et, invalidálódik ha a forrás fájlok módosultak
- A `project_context.py` `load_project_context()` először a cache-t nézi, ha friss, azt használja a nyers fájlok helyett
- A widget frontend a projekt dropdown `onChange` eventjére triggereli az indexelést, így mire a hívás indul, a cache kész

## Capabilities

### New Capabilities
- `project-index-generator`: Claude-alapú projekt összefoglaló generálás — beolvassa az összes docs/*.md és openspec/ fájlt, strukturált összefoglalót készít (modulok, design, állapot, korábbi kérések)
- `index-cache`: Fájl-alapú cache az indexelt összefoglalókhoz, mtime-alapú invalidációval

### Modified Capabilities

## Impact

- `src/project_context.py` — load_project_context() cache-aware lesz
- `src/webhook.py` — új `/api/index-project` endpoint
- `static/voice-widget.html` — projekt dropdown onChange triggereli az indexelést
- Új függőség: nincs (Claude Haiku már elérhető az anthropic SDK-n keresztül)
