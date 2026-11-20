#!/usr/bin/env python3
"""352 Pronostici - Football-Data.org v4 + TheSportsDB (Serie B & C) + analisi Gemini con cache."""
import os, re, json, time, unicodedata, datetime as dt, requests

FD_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_API_KEY") or os.environ.get("FOOTBALL_API_KEY") or os.environ["FD_API_KEY"]
GM_KEY = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
SDB_KEY = os.environ.get("THESPORTSDB_API_KEY") or "123"  # Chiave pubblica gratuita V1

GIORNI = 1                  # finestra di ricerca (giorni)
PAUSA = 2                   # pausa tra chiamate Gemini
PAUSA_FD = 6.2              # pausa tra chiamate Football-Data (piano Free: 10/min)
PAUSA_SDB = 2.2             # pausa tra chiamate TheSportsDB (piano Free: 30/min)
CACHE_GIORNI = 7            # validita cache rose (giorni)
CACHE_CLASSIFICHE_ORE = 12  # validita cache classifiche (ore)
SDB_OFFSET = 900_000_000    # offset numerico per evitare collisioni ID con Football-Data

OUT = "public/data/matches.json"
SQ = "public/data/squads_cache.json"
CL_CACHE = "public/data/standings_cache.json"

# Campionati gestiti da Football-Data.org
COMP = {
    "SA": "Serie A", "PL": "Premier League", "PD": "La Liga", "BL1": "Bundesliga",
    "FL1": "Ligue 1", "CL": "Champions League", "ELC": "Championship", "DED": "Eredivisie",
    "PPL": "Primeira Liga", "BSA": "Serie A Brasile", "WC": "Mondiali FIFA", "EC": "Europei UEFA"
}

# Campionati aggiuntivi gestiti da TheSportsDB (esclusi quelli sopra)
SDB_COMP = {
    "SB": ("4394", "Serie B"),
    "SCA": ("5340", "Serie C - Gir. A"),
    "SCB": ("5339", "Serie C - Gir. B"),
    "SCC": ("4398", "Serie C - Gir. C"),
}

ALL_COMP = {**COMP, **{k: v[1] for k, v in SDB_COMP.items()}}
PATTERN = {"vertical", "horizontal", "diagonal", "half", "solid"}
FORB = re.compile(r"\b(bet\w*|scommess\w*|quot[ae]|bookmaker\w*|puntat\w*|odds?|stake|euro|denaro|soldi|jackpot)\b|[€$£]", re.I)

PROMPT = """Sei un analista statistico di calcio. Partita: {casa} vs {trasf} ({comp}), {data} UTC.
CLASSIFICA/FORMA: {classifica}
ROSA UFFICIALE {casa}: {rosa_c}
ROSA UFFICIALE {trasf}: {rosa_t}
VINCOLO ASSOLUTO: i titolari delle formazioni, i marcatori e gli ammoniti devono essere SOLO giocatori presenti nelle rose qui sopra (nome identico). Nessun giocatore esterno.
Rispondi SOLO con JSON valido, senza testo extra, senza alcun riferimento a scommesse, quote, bookmaker o denaro:
{{"analisi":"3-4 frasi su forma, rendimento casa/trasferta e duelli tattici",
"formazioni":{{"casa":{{"modulo":"4-3-3","undici":["11 nomi"]}},"trasferta":{{"modulo":"4-4-2","undici":["11 nomi"]}}}},
"prob_1x2":{{"1":0,"X":0,"2":0}},
"mercati_completi":{{"1X":0,"X2":0,"12":0,"GG":0,"NG":0,"U1.5":0,"O1.5":0,"U2.5":0,"O2.5":0,"U3.5":0,"O3.5":0,"MG1-3":0,"MG2-4":0,"1+O1.5":0,"1X+GG":0,"2+U3.5":0}},
"possibili_marcatori":[{{"squadra":"casa","giocatore":"","ruolo":"","prob":0}}],
"possibili_ammoniti":[{{"squadra":"casa","giocatore":"","ruolo":"","motivo":"motivazione tattica","prob":0}}],
"pronostico_principale":{{"esito":"1X","probabilita":0,"motivazione_breve":"max 90 caratteri"}},
"affidabilita":0,
"stemma_casa":{{"colori":["#hex","#hex"],"pattern":"vertical|horizontal|diagonal|half|solid"}},
"stemma_trasf":{{"colori":["#hex","#hex"],"pattern":"vertical|horizontal|diagonal|half|solid"}}}}
Regole: probabilita intere 0-100 coerenti (1+X+2=100; U+O della stessa linea=100; GG+NG=100); 2 marcatori e 2 ammoniti per squadra;
squadra = "casa" o "trasferta"; esito di pronostico_principale scelto tra i mercati (es. "1X","Over 2.5","Esito 1","Gol");
colori = i 2 colori HEX reali e fedeli alle maglie ufficiali; pattern = strisce reali della maglia (vertical, horizontal, diagonal, half, solid)."""


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s).strip()


def ok(nome, rosa):
    n = norm(nome)
    if not n:
        return False
    tn = set(n.split())
    return any(n == r or tn <= set(r.split()) or (len(n) > 4 and n in r) for r in rosa)


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


def stagione_corrente():
    oggi = dt.date.today()
    anno = oggi.year if oggi.month >= 7 else oggi.year - 1
    return f"{anno}-{anno + 1}"


def fd(path, params=None):
    for _ in range(3):
        try:
            r = requests.get("https://football-data.org" + path, headers={"X-Auth-Token": FD_KEY},
                             params=params, timeout=30)
        except Exception as e:
            print(path, e, flush=True)
            time.sleep(PAUSA_FD)
            continue
        time.sleep(PAUSA_FD)
        if r.status_code == 429:
            print("Rate limit Football-Data, attendo 35s...", flush=True)
            time.sleep(35)
            continue
        if r.status_code != 200:
            print(path, "HTTP", r.status_code, flush=True)
            return None
        return r.json()
    return None


def sdb(endpoint, params=None):
    """Client HTTP per TheSportsDB V1."""
    url = f"https://www.thesportsdb.com/api/v1/json/{SDB_KEY}/{endpoint}"
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=30)
        except Exception as e:
            print("SDB", endpoint, e, flush=True)
            time.sleep(PAUSA_SDB)
            continue
        time.sleep(PAUSA_SDB)
        if r.status_code == 429:
            print("Rate limit TheSportsDB, attendo 25s...", flush=True)
            time.sleep(25)
            continue
        if r.status_code != 200:
            print("SDB", endpoint, "HTTP", r.status_code, flush=True)
            return None
        return r.json()
    return None


def scegli_modello(vecchio_modello=None):
    if vecchio_modello:
        return vecchio_modello
    try:
        u = "https://googleapis.com"
        r = requests.get(u, params={"key": GM_KEY, "pageSize": 200}, timeout=20).json()
        nomi = [m["name"].split("/")[-1] for m in r.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception as e:
        print("Elenco modelli non disponibile:", e, flush=True)
        nomi = []
    for p in ("gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3-flash-preview"):
        if p in nomi:
            return p
    return "gemini-2.5-flash"


def partite_fd():
    oggi = dt.date.today()
    fine = oggi + dt.timedelta(days=GIORNI)
    j = fd("/matches", {
        "competitions": ",".join(COMP.keys()),
        "dateFrom": oggi.isoformat(),
        "dateTo": fine.isoformat()
    })
    if j is None:
        return None
    res = []
    for m in j.get("matches", []):
        c = (m.get("competition") or {}).get("code")
        if c in COMP:
            m["_c"] = c
            m["_src"] = "fd"
            res.append(m)
    return res


def partite_sdb():
    """Scarica partite di Serie B e Serie C da TheSportsDB normalizzandole nel formato standard."""
    oggi = dt.date.today()
    fine = oggi + dt.timedelta(days=GIORNI)
    date_valide = {(oggi + dt.timedelta(days=i)).isoformat() for i in range(GIORNI + 1)}
    res = []
    visti = set()

    for code, (lid, _) in SDB_COMP.items():
        # Controlla sia i prossimi match che gli ultimi (per aggiornare i risultati appena conclusi)
        for ep in ("eventsnextleague.php", "eventspastleague.php"):
            j = sdb(ep, {"id": lid})
            for ev in (j or {}).get("events") or []:
                d_ev = (ev.get("dateEvent") or "")[:10]
                eid = ev.get("idEvent")
                if not eid or d_ev not in date_valide or eid in visti:
                    continue
                visti.add(eid)

                raw_st = (ev.get("strStatus") or "").upper()
                hs, as_ = ev.get("intHomeScore"), ev.get("intAwayScore")
                if raw_st in ("FT", "AET", "PEN", "FINISHED") or (hs is not None and as_ is not None and raw_st in ("", "FT")):
                    stato = "FINISHED"
                elif raw_st in ("1H", "2H", "ET", "P", "LIVE", "IN_PLAY"):
                    stato = "IN_PLAY"
                elif raw_st in ("HT", "BT", "PAUSED"):
                    stato = "PAUSED"
                else:
                    stato = "TIMED"

                ora = (ev.get("strTime") or "15:00:00")[:8]
                if len(ora) == 5:
                    ora += ":00"
                hid = int(ev.get("idHomeTeam") or 0)
                aid = int(ev.get("idAwayTeam") or 0)

                res.append({
                    "id": SDB_OFFSET + int(eid),
                    "_c": code,
                    "_src": "sdb",
                    "utcDate": f"{d_ev}T{ora}Z",
                    "status": stato,
                    "homeTeam": {"id": SDB_OFFSET + hid if hid else 0, "name": ev.get("strHomeTeam") or ""},
                    "awayTeam": {"id": SDB_OFFSET + aid if aid else 0, "name": ev.get("strAwayTeam") or ""},
                    "score": {
                        "fullTime": {
                            "home": int(hs) if hs is not None and str(hs).isdigit() else None,
                            "away": int(as_) if as_ is not None and str(as_).isdigit() else None
                        }
                    }
                })
    return res


