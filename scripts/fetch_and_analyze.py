#!/usr/bin/env python3
"""352 Pronostici - Football-Data + TheSportsDB + OpenLigaDB + Gemini AI (con cache)."""
import os, re, json, time, datetime as dt, requests

FD_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_API_KEY") or os.environ.get("FOOTBALL_API_KEY") or os.environ.get("FD_API_KEY", "")
GM_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
SDB_KEY = os.environ.get("THESPORTSDB_API_KEY") or "123"

GIORNI = 3
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
def scegli_modello(vecchio_modello=None):
    if vecchio_modello:
        return vecchio_modello
    try:
        r = requests.get(GM_BASE, params={"key": GM_KEY, "pageSize": 200}, timeout=20).json()
        nomi = [m["name"].split("/")[-1] for m in r.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception:
        nomi = []
    for p in ("gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash", "gemini-3-flash-preview"):
        if p in nomi:
            return p
    return "gemini-3.5-flash-lite"

def partite_fd():
    oggi = dt.date.today()
    fine = oggi + dt.timedelta(days=GIORNI)
    j = fd("/matches", {"competitions": ",".join(COMP.keys()), "dateFrom": oggi.isoformat(), "dateTo": fine.isoformat()})
    if j is None:
        return []
    res = []
    for m in j.get("matches", []):
        c = (m.get("competition") or {}).get("code")
        if c not in COMP:
            continue
        ft = (m.get("score") or {}).get("fullTime") or {}
        hs, as_ = ft.get("home"), ft.get("away")
        res.append({
            "id": m["id"],
            "comp": c,
            "compNome": COMP[c],
            "data": m.get("utcDate") or "",
            "stato": m.get("status") or "TIMED",
            "casa": (m.get("homeTeam") or {}).get("name") or "",
            "trasf": (m.get("awayTeam") or {}).get("name") or "",
            "score": [hs, as_] if hs is not None and as_ is not None else None,
            "_hid": (m.get("homeTeam") or {}).get("id") or 0,
            "_aid": (m.get("awayTeam") or {}).get("id") or 0
        })
    return res

def partite_sdb():
    oggi = dt.date.today()
    date_valide = {(oggi + dt.timedelta(days=i)).isoformat() for i in range(GIORNI + 1)}
    res = []
    visti = set()
    for code, (lid, cnome) in SDB_COMP.items():
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
                h_ok = hs is not None and str(hs).isdigit()
                a_ok = as_ is not None and str(as_).isdigit()
                res.append({
                    "id": SDB_OFFSET + int(eid),
                    "comp": code,
                    "compNome": cnome,
                    "data": f"{d_ev}T{ora}Z",
                    "stato": stato,
                    "casa": ev.get("strHomeTeam") or "",
                    "trasf": ev.get("strAwayTeam") or "",
                    "score": [int(hs), int(as_)] if (h_ok and a_ok) else None,
                    "_hid": SDB_OFFSET + hid if hid else 0,
                    "_aid": SDB_OFFSET + aid if aid else 0
                })
    return res

def partite_ol():
    oggi = dt.date.today()
    date_valide = {(oggi + dt.timedelta(days=i)).isoformat() for i in range(GIORNI + 1)}
    res = []
    for code, (shortcut, cnome) in OL_COMP.items():
        data = ol(f"/getmatchdata/{shortcut}")
        for m in data or []:
            d_ev = (m.get("matchDateTimeUTC") or "")[:10]
            mid = m.get("matchID")
            if not mid or d_ev not in date_valide:
                continue
            finito = m.get("matchIsFinished", False)
            risultati = m.get("matchResults") or []
            finale = next((r for r in risultati if r.get("resultTypeID") == 2), risultati[-1] if risultati else {})
            hs, as_ = finale.get("pointsTeam1"), finale.get("pointsTeam2")
            res.append({
                "id": OL_OFFSET + int(mid),
                "comp": code,
                "compNome": cnome,
                "data": m.get("matchDateTimeUTC") or f"{d_ev}T15:00:00Z",
                "stato": "FINISHED" if finito else "TIMED",
                "casa": (m.get("team1") or {}).get("teamName") or "",
                "trasf": (m.get("team2") or {}).get("teamName") or "",
                "score": [hs, as_] if hs is not None and as_ is not None else None,
                "_hid": OL_OFFSET + int((m.get("team1") or {}).get("teamId") or 0),
                "_aid": OL_OFFSET + int((m.get("team2") or {}).get("teamId") or 0)
            })
    return res

def get_rosa(team_id, cache):
    if not team_id:
        return []
    tid_str = str(team_id)
    ora_ts = time.time()
    if tid_str in cache and (ora_ts - cache[tid_str].get("ts", 0)) < CACHE_GIORNI * 86400:
        return cache[tid_str].get("players", [])
    players = []
    if team_id >= SDB_OFFSET:
        j = sdb("lookup_all_players.php", {"id": team_id - SDB_OFFSET})
        players = [p.get("strPlayer") for p in (j or {}).get("player") or [] if p.get("strPlayer")]
    elif team_id < OL_OFFSET:
        j = fd(f"/teams/{team_id}")
        players = [p.get("name") for p in (j or {}).get("squad") or [] if p.get("name")]
    cache[tid_str] = {"ts": ora_ts, "players": players}
    return players

def analizza_gemini(modello, m, rosa_c, rosa_t):
    prompt = PROMPT.format(
        casa=m["casa"],
        trasf=m["trasf"],
        comp=m["compNome"],
        data=m["data"],
        classifica="Dati standard di campionato",
        rosa_c=", ".join(rosa_c[:25]) if rosa_c else "Non disponibile",
        rosa_t=", ".join(rosa_t[:25]) if rosa_t else "Non disponibile"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}
    }
    modelli_prova = list(dict.fromkeys([modello, "gemini-3.5-flash", "gemini-3-flash-preview"]))
    for mod in modelli_prova:
        url = f"{GM_BASE}/{mod}:generateContent"
        for _ in range(2):
            try:
                r = requests.post(url, params={"key": GM_KEY}, json=payload, timeout=45)
                time.sleep(PAUSA)
                if r.status_code == 200:
                    data = r.json()
                    cand = next(iter(data.get("candidates") or []), {})
                    part = next(iter((cand.get("content") or {}).get("parts") or []), {})
                    txt = part.get("text", "{}")
                    return pulisci(json.loads(txt))
                if r.status_code in (429, 500, 503):
                    print(f"Modello {mod} occupato ({r.status_code}), passo al successivo...", flush=True)
                    time.sleep(3)
                    break
                print("Errore Gemini:", mod, r.status_code, r.text[:150], flush=True)
                break
            except Exception as e:
                print("Eccezione Gemini:", e, flush=True)
                time.sleep(2)
    return {}


def main():
    vecchio = load_json(OUT, {"matches": []})
    lista_vecchia = vecchio if isinstance(vecchio, list) else (vecchio.get("matches") or vecchio.get("partite") or [])
    vecchie_map = {m["id"]: m for m in lista_vecchia if isinstance(m, dict) and "id" in m}
    sq_cache = load_json(SQ, {})
    cl_cache = load_json(CL_CACHE, {})

    partite = partite_fd() + partite_sdb() + partite_ol()
    print(f"Trovate {len(partite)} partite totali da elaborare...", flush=True)
    modello = scegli_modello()
    risultati = []

    for idx, m in enumerate(partite, 1):
        mid = m["id"]
        prev = vecchie_map.get(mid)
        if prev and prev.get("prob_1x2"):
            prev["stato"] = m["stato"]
            prev["score"] = m["score"]
            risultati.append(prev)
            continue

        print(f"[{idx}/{len(partite)}] Analisi {m['casa']} - {m['trasf']}...", flush=True)
        rosa_c = get_rosa(m.pop("_hid", 0), sq_cache)
        rosa_t = get_rosa(m.pop("_aid", 0), sq_cache)
        ai_data = analizza_gemini(modello, m, rosa_c, rosa_t)
        m.update(ai_data)
        risultati.append(m)

    save_json(SQ, sq_cache)
    save_json(CL_CACHE, cl_cache)
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    save_json(OUT, {"updated_at": now_iso, "aggiornato": now_iso, "matches": risultati, "partite": risultati}, indent=2)
    print(f"Salvate {len(risultati)} partite in {OUT}", flush=True)

if __name__ == "__main__":
    main()
