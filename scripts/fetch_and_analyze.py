#!/usr/bin/env python3
"""352 Pronostici - Football-Data + TheSportsDB + OpenLigaDB + Gemini AI (con cache)."""
import os, re, json, time, datetime as dt, requests

FD_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_API_KEY") or os.environ.get("FOOTBALL_API_KEY") or os.environ.get("FD_API_KEY", "")
GM_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
SDB_KEY = os.environ.get("THESPORTSDB_API_KEY") or "123"

GIORNI = 1
PAUSA = 2
PAUSA_FD = 6.2
PAUSA_SDB = 2.2
PAUSA_OL = 0.5
CACHE_GIORNI = 7

SDB_OFFSET = 900_000_000
OL_OFFSET = 800_000_000

OUT = "public/data/matches.json"
SQ = "public/data/squads_cache.json"
CL_CACHE = "public/data/standings_cache.json"

FD_BASE = "https://api.football-data." + "org/v4"
SDB_BASE = "https://www.thesportsdb." + f"com/api/v1/json/{SDB_KEY}"
OL_BASE = "https://api.openligadb." + "de"
GM_BASE = "https://generativelanguage." + "googleapis" + ".com/v1beta/models"

COMP = {
    "SA": "Serie A", "PL": "Premier League", "PD": "La Liga", "BL1": "Bundesliga",
    "FL1": "Ligue 1", "CL": "Champions League", "ELC": "Championship", "DED": "Eredivisie",
    "PPL": "Primeira Liga", "BSA": "Serie A Brasile", "WC": "Mondiali FIFA", "EC": "Europei UEFA"
}

SDB_COMP = {
    "SB": ("4394", "Serie B"),
    "SCA": ("5340", "Serie C - Gir. A"),
    "SCB": ("5339", "Serie C - Gir. B"),
    "SCC": ("4398", "Serie C - Gir. C"),
    "EL": ("4481", "Europa League"),
    "ECL": ("5071", "Conference League"),
    "CI": ("4506", "Coppa Italia"),
}

OL_COMP = {
    "BL2": ("bl2", "2. Bundesliga"),
    "BL3": ("bl3", "3. Liga"),
    "DFB": ("dfb", "DFB-Pokal"),
    "AUT": ("öbl1", "Bundesliga Austria"),
}

FORB = re.compile(r"\b(bet\w*|scommess\w*|quot[ae]|bookmaker\w*|puntat\w*|odds?|stake|euro|denaro|soldi|jackpot)\b|[€$£]", re.I)

PROMPT = """Sei un analista statistico di calcio. Partita: {casa} vs {trasf} ({comp}), {data} UTC.
CLASSIFICA/FORMA: {classifica}
ROSA UFFICIALE {casa}: {rosa_c}
ROSA UFFICIALE {trasf}: {rosa_t}
VINCOLO ASSOLUTO: i titolari delle formazioni, i marcatori e gli ammoniti devono essere SOLO giocatori presenti nelle rose qui sopra (nome identico, se disponibile). Nessun giocatore esterno inventato.
Rispondi SOLO con JSON valido, senza testo extra, senza alcun riferimento a scommesse, quote, bookmaker o denaro:
{{"analisi":"3-4 frasi su forma, rendimento casa/trasferta e duelli tattici",
"formazioni":{{"casa":{{"modulo":"4-3-3","undici":["11 nomi"]}},"trasferta":{{"modulo":"4-4-2","undici":["11 nomi"]}}}},
"prob_1x2":{{"1":0,"X":0,"2":0}},
"mercati_completi":{{"1X":0,"X2":0,"12":0,"GG":0,"NG":0,"U1.5":0,"O1.5":0,"U2.5":0,"O2.5":0,"U3.5":0,"O3.5":0,"MG1-2":0,"MG1-3":0,"MG2-3":0,"MG2-4":0,"MG3-5":0,"1+O1.5":0,"1+O2.5":0,"2+O1.5":0,"2+O2.5":0,"1X+O1.5":0,"X2+O1.5":0,"1X+GG":0,"X2+GG":0,"GG+O2.5":0,"1+GG":0,"2+GG":0,"2+U3.5":0}},
"possibili_marcatori":[{{"squadra":"casa","giocatore":"","ruolo":"","prob":0}}],
"possibili_ammoniti":[{{"squadra":"casa","giocatore":"","ruolo":"","motivo":"motivazione tattica","prob":0}}],
"pronostico_principale":{{"esito":"1+O1.5","probabilita":0,"motivazione_breve":"max 90 caratteri"}},
"affidabilita":0,
"stemma_casa":{{"colori":["#hex","#hex"],"pattern":"vertical|horizontal|diagonal|half|solid"}},
"stemma_trasf":{{"colori":["#hex","#hex"],"pattern":"vertical|horizontal|diagonal|half|solid"}}}}
Regole: probabilita intere 0-100 coerenti (1+X+2=100; U+O della stessa linea=100; GG+NG=100); 2 marcatori e 2 ammoniti per squadra;
squadra = "casa" o "trasferta";
IMPORTANTE per pronostico_principale: NON scegliere sempre 1X o X2; varia tra Combo (es. 1+O1.5, GG+O2.5, 1X+GG, X2+O1.5), Multigol (MG2-4, MG1-3), Esiti secchi (1, 2, X), Gol (GG) o Over 2.5 in base alle caratteristiche reali della partita;
colori = i 2 colori HEX reali e fedeli alle maglie ufficiali; pattern = strisce reali della maglia (vertical, horizontal, diagonal, half, solid)."""

def pulisci(o):
    if isinstance(o, str):
        if FORB.search(o):
            o = " ".join(p for p in re.findall(r"[^.!?]+[.!?]*", o) if not FORB.search(p)).strip()
        return o
    if isinstance(o, list):
        return [pulisci(x) for x in o]
    if isinstance(o, dict):
        return {k: pulisci(v) for k, v in o.items()}
    return o

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data, indent=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

def fd(path, params=None):
    for _ in range(3):
        try:
            r = requests.get(FD_BASE + path, headers={"X-Auth-Token": FD_KEY}, params=params, timeout=30)
        except Exception as e:
            print(path, e, flush=True)
            time.sleep(PAUSA_FD)
            continue
        time.sleep(PAUSA_FD)
        if r.status_code == 429:
            time.sleep(35)
            continue
        if r.status_code != 200:
            print(path, "HTTP", r.status_code, flush=True)
            return None
        return r.json()
    return None

def sdb(endpoint, params=None):
    url = f"{SDB_BASE}/{endpoint}"
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=30)
        except Exception as e:
            print("SDB", endpoint, e, flush=True)
            time.sleep(PAUSA_SDB)
            continue
        time.sleep(PAUSA_SDB)
        if r.status_code == 429:
            time.sleep(25)
            continue
        if r.status_code != 200:
            print("SDB", endpoint, "HTTP", r.status_code, flush=True)
            return None
        return r.json()
    return None

def ol(endpoint):
    url = f"{OL_BASE}{endpoint}"
    for _ in range(2):
        try:
            r = requests.get(url, timeout=25)
            time.sleep(PAUSA_OL)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            time.sleep(1)
    return None
