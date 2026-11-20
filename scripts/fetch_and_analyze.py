#!/usr/bin/env python3
"""352 Pronostici - partite, rose reali e classifiche (Football-Data.org v4) + analisi Gemini (Ottimizzato)."""
import os, re, json, time, unicodedata, datetime as dt, requests

FD_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_API_KEY") or os.environ.get("FOOTBALL_API_KEY") or os.environ["FD_API_KEY"]
GM_KEY = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]

GIORNI = 1                  # finestra di ricerca (giorni)
PAUSA = 2                   # pausa tra chiamate Gemini
PAUSA_FD = 6.2              # pausa tra chiamate Football-Data (piano Free: 10/min)
CACHE_GIORNI = 7            # validita cache rose (giorni)
CACHE_CLASSIFICHE_ORE = 12  # validita cache classifiche (ore)

OUT = "public/data/matches.json"
SQ = "public/data/squads_cache.json"
CL_CACHE = "public/data/standings_cache.json"

COMP = {"SA": "Serie A", "PL": "Premier League", "PD": "La Liga", "BL1": "Bundesliga",
        "FL1": "Ligue 1", "CL": "Champions League", "ELC": "Championship", "DED": "Eredivisie",
        "PPL": "Primeira Liga", "BSA": "Serie A Brasile", "WC": "Mondiali FIFA", "EC": "Europei UEFA"}
PATTERN = {"vertical", "horizontal", "diagonal", "half", "solid"}
# Compliance editoriale: nessun riferimento a scommesse, quote, bookmaker, puntate o denaro
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


def scegli_modello(vecchio_modello=None):
    # Evita una chiamata HTTP inutile se il modello era gia stato rilevato
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


def partite():
    """Scarica tutte le partite delle 12 competizioni in UNA sola chiamata API invece di 12."""
    oggi = dt.date.today()
    fine = oggi + dt.timedelta(days=GIORNI)
    j = fd("/matches", {
        "competitions": ",".join(COMP.keys()),
        "dateFrom": oggi.isoformat(),
        "dateTo": fine.isoformat()
    })
    if j is None:
        return None  # Segnala errore di rete per non sovrascrivere la cache valida
    res = []
    for m in j.get("matches", []):
        c = (m.get("competition") or {}).get("code")
        if c in COMP:
            m["_c"] = c
            res.append(m)
    return res


def carica_rose(team_ids):
    if not team_ids:
        return load_json(SQ, {})
    cache = load_json(SQ, {})
    limite = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=CACHE_GIORNI)).isoformat()
    da_scaricare = [tid for tid in team_ids if not cache.get(str(tid)) or cache[str(tid)].get("ts", "") < limite]
    print(f"Rose da aggiornare: {len(da_scaricare)} su {len(team_ids)}", flush=True)
    for idx, tid in enumerate(da_scaricare, 1):
        print(f"  [{idx}/{len(da_scaricare)}] Scarico rosa team {tid}...", flush=True)
        j = fd(f"/teams/{tid}")
        if j and j.get("squad"):
            cache[str(tid)] = {
                "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
                "squad": [{"name": p.get("name"), "position": p.get("position"), "shirtNumber": p.get("shirtNumber")} for p in j["squad"]]
            }
        if idx % 10 == 0:
            save_json(SQ, cache)
    if da_scaricare:
        save_json(SQ, cache)
    return cache


def classifiche(codici):
    """Cache classifiche valida 12 ore: scarica solo se scaduta o mancante."""
    if not codici:
        return {}
    cache = load_json(CL_CACHE, {})
    limite = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=CACHE_CLASSIFICHE_ORE)).isoformat()
    res = {}
    aggiornata = False

    for c in codici:
        entry = cache.get(c)
        if entry and entry.get("ts", "") >= limite and entry.get("righe"):
            res[c] = {int(k): v for k, v in entry["righe"].items()}
            continue

        print(f"Scarico classifica per {COMP.get(c, c)}...", flush=True)
        j = fd(f"/competitions/{c}/standings")
        righe = {}
        for s in (j or {}).get("standings", []):
            if s.get("type") != "TOTAL":
                continue
            for r in s.get("table", []):
                righe[r["team"]["id"]] = (f'{r["position"]}o {r["team"]["name"]}: {r["points"]} punti in '
                                          f'{r["playedGames"]} gare, DR {r["goalDifference"]}, forma {r.get("form") or "n.d."}')
        if righe:
            cache[c] = {
                "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
                "righe": {str(k): v for k, v in righe.items()}
            }
            aggiornata = True
        res[c] = righe

    if aggiornata:
        save_json(CL_CACHE, cache)
    return res


def rosa_txt(cache, tid):
    return ", ".join(f'{p["name"]} ({(p.get("position") or "?")[:12]})' for p in cache.get(str(tid), {}).get("squad", []))


def analizza(modello, m, cache, cl):
    hid, aid = m["homeTeam"]["id"], m["awayTeam"]["id"]
    casa_nome, trasf_nome = m["homeTeam"]["name"], m["awayTeam"]["name"]
    print(f"Analisi AI: {casa_nome} vs {trasf_nome}...", flush=True)
    righe = cl.get(m["_c"], {})
    p = PROMPT.format(casa=casa_nome, trasf=trasf_nome, comp=COMP[m["_c"]], data=m["utcDate"],
                      classifica=" | ".join(x for x in (righe.get(hid), righe.get(aid)) if x) or "n.d.",
                      rosa_c=rosa_txt(cache, hid) or "n.d.", rosa_t=rosa_txt(cache, aid) or "n.d.")
    url = "https://googleapis.com/" + modello + ":generateContent"

    for tentativo in range(4):
        try:
            r = requests.post(url, params={"key": GM_KEY}, timeout=60, json={
                "contents": [{"parts": [{"text": p}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3}})
            if r.status_code == 429:
                print(f"Rate limit Gemini ({tentativo + 1}/4), attendo 35s...", flush=True)
                time.sleep(35)
