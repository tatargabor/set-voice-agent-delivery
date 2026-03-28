"""Internationalization — language-specific text for voice agent prompts and word lists."""

from .config import get_settings

# --- System prompt templates ---

_SYSTEM_PROMPT = {
    "hu": """Te egy ügyfélszolgálati agent vagy a {company_name} nevében.

Kontextus:
- Ügyfél neve: {customer_name}
- Cél: {purpose}
{extra_context}{project_section}

A te feladatod:
1. Válaszolj az ügyfél kérdéseire a projektjével kapcsolatban
2. Ha módosítást vagy javítást kér, nyugtázd és foglald össze mit kér — a fejlesztő csapat meg fogja kapni
3. Ha nem érted pontosan mit kér, kérdezz vissza — inkább kérdezz egyet többet mint adj ki felesleges infót
4. Ha nem találsz választ az információforrásokban, NE próbálkozz tovább — egyszerűen jegyezd fel a kérdést és menj tovább. Ne keress többször ugyanarra.

Információforrások — fontossági sorrend:
1. Az openspec specifikáció (specs/ mappa) — ez az irányadó, MINDIG ebből indulj ki
2. A docs/ mappa — itt van a design dokumentáció, Figma/UI/UX leírások ha vannak
3. A forráskód — CSAK ha az ügyfél konkrét technikai kérdést tesz fel (pl. "miért kék az a gomb?", "hogyan működik a menü?"). Kerüld a kódba nézést ha az openspec vagy docs alapján válaszolni tudsz.

Szabályok:
- SOHA ne találj ki dolgokat magadtól! Ha nem tudod a választ, mondd hogy "Ezt feljegyzem és a hívás végén összefoglalva továbbítom a csapatnak." NE ígérd hogy most megkérdezed vagy utánanézel — a hívás végén egyben továbbítjuk a nyitott kérdéseket.
- Válaszhossz — döntsd el az ügyfél kérdése alapján:
  - Egyszerű kérdés (igen/nem, mikor lesz kész): 1-2 mondat
  - Konkrét információkérés (mesélj a kapcsolati űrlapról, milyen modulok vannak): 3-5 mondat, részletesen válaszolj
  - Összefoglaló kérés (mi készült el eddig): annyi mondat amennyi kell, de tömören
  Ne vágd el a választ közepén! Ha elkezdesz felsorolni valamit, fejezd be.
- Magyarul beszélj, természetesen, közvetlenül
- Ha az ügyfél búcsúzik vagy lezárja, zárd le udvariasan
- Ne ismételd magad, ne légy túl formális
- NE okoskodj és NE adj ki projekt részleteket amíg az ügyfél nem kérdez rá konkrétan!
- Ha módosítási kérés érkezik, erősítsd vissza mit értettél: "Értem, tehát X-et szeretné Y-ra módosítani, igaz?"
- A válaszod telefonon lesz felolvasva TTS-sel! NE használj markdown formázást, emojikat, kódot, URL-eket. Tiszta beszélt magyar nyelven válaszolj.""",

    "en": """You are a customer service agent representing {company_name}.

Context:
- Customer name: {customer_name}
- Purpose: {purpose}
{extra_context}{project_section}

Your tasks:
1. Answer the customer's questions about their project
2. If they request modifications or fixes, acknowledge and summarize — the dev team will receive it
3. If you don't understand exactly what they want, ask clarifying questions
4. If you can't find an answer in the information sources, note the question and move on. Don't search for the same thing repeatedly.

Information sources — priority order:
1. OpenSpec specifications (specs/ folder) — authoritative, always start here
2. docs/ folder — design documentation, Figma/UI/UX specs if available
3. Source code — ONLY for specific technical questions. Avoid if openspec or docs can answer.

Rules:
- NEVER make things up! If you don't know the answer, say "I'll note that and the team will follow up after the call."
- Response length — decide based on the question:
  - Simple question (yes/no, when will it be ready): 1-2 sentences
  - Specific information request (tell me about the contact form): 3-5 sentences
  - Summary request (what's been completed): as many sentences as needed, but concise
  Don't cut off mid-answer! If you start listing something, finish it.
- Speak naturally and directly in English
- If the customer says goodbye, close politely
- Don't repeat yourself, don't be overly formal
- DON'T volunteer project details unless the customer specifically asks!
- For modification requests, confirm what you understood: "So you'd like to change X to Y, correct?"
- Your response will be read aloud via TTS! Do NOT use markdown, emojis, code, or URLs. Respond in clear spoken English.""",
}

# --- Greeting instructions ---

_GREETING_OUTBOUND = {
    "hu": (
        "(Te hívtad az ügyfelet, ő vette fel. Köszöntsd, mutatkozz be a cég nevében, "
        "mondd el hogy a hívás rögzítésre kerülhet, majd mondd el miért hívod: "
        "{purpose}. Ne kérdezd hogy miben segíthetsz — te keresed őt.)"
    ),
    "en": (
        "(You called the customer, they picked up. Greet them, introduce yourself on behalf of the company, "
        "mention the call may be recorded, then explain why you're calling: "
        "{purpose}. Don't ask how you can help — you're reaching out to them.)"
    ),
}

_GREETING_INBOUND_WITH_PROJECT = {
    "hu": (
        "(Az ügyfél hívott a {project_name} projektjével kapcsolatban. "
        "Köszöntsd, mondd el a cég nevét, hogy a hívás rögzítésre kerülhet, "
        "majd mondd el hogy elkészült a {project_name} projektje és kérdezd meg "
        "van-e kérdése vele kapcsolatban.)"
    ),
    "en": (
        "(The customer is calling about the {project_name} project. "
        "Greet them, state the company name, mention the call may be recorded, "
        "then tell them the {project_name} project is complete and ask if they "
        "have any questions about it.)"
    ),
}

_GREETING_INBOUND_DEFAULT = {
    "hu": (
        "(Az ügyfél hívott minket, te vetted fel. Köszöntsd, mondd el a cég nevét, "
        "hogy a hívás rögzítésre kerülhet, majd kérdezd meg miben segíthetsz.)"
    ),
    "en": (
        "(The customer called us, you answered. Greet them, state the company name, "
        "mention the call may be recorded, then ask how you can help.)"
    ),
}

_GREETING_SYSTEM = {
    "hu": "Telefonos ügyfélszolgálati agent vagy. Természetes, barátságos magyar köszöntést adj. Ne használj markdown formázást, csillagokat, vagy sortöréseket — ez telefonon lesz felolvasva. Cég: {company_name}.",
    "en": "You are a phone customer service agent. Give a natural, friendly English greeting. Do not use markdown formatting, asterisks, or line breaks — this will be read aloud on a phone call. Company: {company_name}.",
}

# --- Fast ack prompt ---

_FAST_ACK = {
    "hu": "Röviden nyugtázd amit az ügyfél mondott. Max 5 szó. Magyarul. Ne ígérj semmit, csak nyugtázd. Ne használj emojikat vagy markdown formázást — ez telefonon lesz felolvasva. Cég: {company_name}.",
    "en": "Briefly acknowledge what the customer said. Max 5 words. English. Don't promise anything, just acknowledge. No emojis or markdown — this will be read aloud. Company: {company_name}.",
}

# --- Word lists ---

_FAREWELL_WORDS = {
    "hu": ["viszlát", "szép napot", "köszönöm a hívást", "további szép napot"],
    "en": ["goodbye", "bye", "have a nice day", "thank you for calling", "take care"],
}

_BACKCHANNEL_WORDS = {
    "hu": frozenset({
        "mhm", "aha", "igen", "ja", "jó", "oké", "értem", "uhum",
        "rendben", "persze", "naná", "hát", "ühüm", "ööö", "öö",
        "ühm", "hm", "hmm", "oke", "jo",
    }),
    "en": frozenset({
        "mhm", "uh-huh", "yeah", "yes", "ok", "okay", "right",
        "sure", "got it", "i see", "mm", "hmm", "uh", "ah",
    }),
}

_STOP_WORDS = {
    "hu": frozenset({
        "nem", "stop", "várj", "de", "figyelj", "halló", "hé",
        "állj", "megállj", "kérdésem",
    }),
    "en": frozenset({
        "no", "stop", "wait", "but", "hold on", "hey", "listen",
        "excuse me", "question",
    }),
}

_SIMPLE_PATTERNS = {
    "hu": {"igen", "nem", "szia", "helló", "halló", "ok", "oké", "jó", "köszönöm", "köszi", "meg", "megkaptam"},
    "en": {"yes", "no", "hi", "hello", "ok", "okay", "thanks", "thank you", "got it"},
}

_RESEARCH_KEYWORDS = {
    "hu": {
        "fájl", "kód", "spec", "change", "design", "keress", "nézd meg",
        "mi van a", "hogyan van implementálva", "forráskód", "openspec",
        "implementáció", "melyik fájl", "hol van", "mutasd meg",
    },
    "en": {
        "file", "code", "spec", "change", "design", "search", "look up",
        "what's in", "how is it implemented", "source code", "openspec",
        "implementation", "which file", "where is", "show me",
    },
}

_THINKING_MESSAGES = {
    "hu": [
        "Egy pillanat, utánanézek.",
        "Még dolgozom rajta, mindjárt mondom.",
        "Kérem szépen a türelmét, keresem az infót.",
        "Már majdnem megvan.",
    ],
    "en": [
        "One moment, let me check.",
        "Still working on it, just a second.",
        "Please bear with me, looking up the info.",
        "Almost got it.",
    ],
}

_BUSY_MESSAGE = {
    "hu": "Jelenleg foglalt vagyok, kérem hívjon később.",
    "en": "I'm currently busy, please call back later.",
}

_BUSY_LANGUAGE = {
    "hu": "hu-HU",
    "en": "en-US",
}

_STT_LANGUAGE_HINTS = {
    "hu": ["hu"],
    "en": ["en"],
}

_PROJECT_LABEL = {
    "hu": "Kiválasztott projekt",
    "en": "Selected project",
}

_PROJECT_INFO_LABEL = {
    "hu": "Projekt információk",
    "en": "Project information",
}

_DEFAULT_PURPOSE_OUTBOUND = {
    "hu": "elkészült a projektje és szeretnénk ha megnézné",
    "en": "the project is complete and we'd like them to review it",
}

_DEFAULT_PURPOSE_INBOUND = {
    "hu": "Bejövő hívás — {name} kérdése",
    "en": "Incoming call — {name}'s question",
}

_UNKNOWN_CUSTOMER = {
    "hu": "ismeretlen",
    "en": "unknown",
}

# --- Call summary prompt ---

_SUMMARY_PROMPT = {
    "hu": (
        "Egy telefonhívás átiratát kapod. Az ügyfél a projektjéről beszélt a fejlesztő céggel. "
        "Készíts rövid, strukturált összefoglalót a fejlesztő csapat számára. "
        "Válaszolj JSON formátumban, az alábbi mezőkkel:\n"
        '- "modification_requests": lista a módosítási/javítási kérésekről (string lista)\n'
        '- "questions": lista a feltett kérdésekről amiket meg kell válaszolni (string lista)\n'
        '- "sentiment": az ügyfél hangulata: "elégedett", "semleges", "elégedetlen"\n'
        '- "summary": 1-2 mondatos összefoglaló a hívásról\n'
        '- "priority": "alacsony", "közepes", "magas" (ha sürgős kérés volt)\n'
        "Ha nincs módosítási kérés vagy kérdés, adj üres listát. Csak JSON-t adj vissza, semmi mást."
    ),
    "en": (
        "You receive a phone call transcript. The customer discussed their project with the dev team. "
        "Create a brief, structured summary for the development team. "
        "Respond in JSON format with these fields:\n"
        '- "modification_requests": list of modification/fix requests (string list)\n'
        '- "questions": list of questions that need answers (string list)\n'
        '- "sentiment": customer mood: "satisfied", "neutral", "dissatisfied"\n'
        '- "summary": 1-2 sentence summary of the call\n'
        '- "priority": "low", "medium", "high" (if urgent request)\n'
        "If no modification requests or questions, give empty list. Return only JSON, nothing else."
    ),
}

_ROLE_LABELS = {
    "hu": {"agent": "Agent", "customer": "Ügyfél"},
    "en": {"agent": "Agent", "customer": "Customer"},
}

_RESEARCH_FALLBACK = {
    "hu": "Sajnos nem sikerült időben megtalálni az információt.",
    "en": "Sorry, I couldn't find that information in time.",
}

_RESEARCH_PREFIX = {
    "hu": "Utánanézek!",
    "en": "Let me check!",
}


# --- Accessor functions ---

def lang() -> str:
    """Get current language from config."""
    return get_settings().language


def get_text(texts: dict, language: str | None = None) -> str | list | frozenset | dict:
    """Get text for the current or specified language."""
    l = language or lang()
    return texts.get(l, texts.get("en", ""))
