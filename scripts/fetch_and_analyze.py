#!/usr/bin/env python3
"""352 Pronostici - partite, rose reali e classifiche (Football-Data.org v4) + analisi Gemini."""
import os, re, json, time, unicodedata, datetime as dt, requests

FD_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_API_KEY") or os.environ.get("FOOTBALL_API_KEY") or os.environ["FD_API_KEY"]
GM_KEY = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
GIORNI = 4          # finestra di ricerca (giorni)
PAUSA = 2           # pausa tra chiamate Gemini
PAUSA_FD = 6.2       # pausa tra chiamate Football-Data (piano Free: 10/min)
CACHE_GIORNI = 7    # validita cache rose
OUT = "public/data/matches.json"
SQ = "public/data/squads_cache.json"
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


def fd(path, params=None):
    for _ in range(3):
        try:
            r = requests.get("https://api.football-data.org/v4" + path, headers={"X-Auth-Token": FD_KEY},
                             params=params, timeout=30)
        except Exception as e:
            print(path, e); time.sleep(PAUSA_FD); continue
        time.sleep(PAUSA_FD)
        if r.status_code == 429:
            time.sleep(35); continue
        if r.status_code != 200:
            print(path, "HTTP", r.status_code)
            return None
        return r.json()
    return None


def scegli_modello():
    return "gemini-2.5-flash"



def partite():
    oggi = dt.date.today(); fine = oggi + dt.timedelta(days=GIORNI); res = []
    for c in COMP:
        j = fd(f"/competitions/{c}/matches", {"dateFrom": oggi.isoformat(), "dateTo": fine.isoformat()})
        for m in (j or {}).get("matches", []):
            m["_c"] = c; res.append(m)
    return res


def carica_rose(team_ids):
    os.makedirs(os.path.dirname(SQ), exist_ok=True)
    try:
        cache = json.load(open(SQ, encoding="utf-8"))
    except Exception:
        cache = {}
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
            json.dump(cache, open(SQ, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(cache, open(SQ, "w", encoding="utf-8"), ensure_ascii=False)
    return cache



def classifiche(codici):
    res = {}
    for c in codici:
        j = fd(f"/competitions/{c}/standings")
        righe = {}
        for s in (j or {}).get("standings", []):
            if s.get("type") != "TOTAL":
                continue
            for r in s.get("table", []):
                righe[r["team"]["id"]] = (f'{r["position"]}o {r["team"]["name"]}: {r["points"]} punti in '
                                          f'{r["playedGames"]} gare, DR {r["goalDifference"]}, forma {r.get("form") or "n.d."}')
        res[c] = righe
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
    url = f"https://googleapis.com{modello}:generateContent"
    for tentativo in range(4):
        try:
            r = requests.post(url, params={"key": GM_KEY}, timeout=60, json={
                "contents": [{"parts": [{"text": p}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3}})
            if r.status_code == 429:
                attesa = 25 + (tentativo * 15)
                print(f"  Rate limit Gemini, attendo {attesa}s...", flush=True)
                time.sleep(attesa)
                continue
            r.raise_for_status()
            t = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            time.sleep(5)
            return json.loads(re.sub(r"^```(?:json)?|```$", "", t.strip()).strip())
        except Exception as e:
            print(f"  Errore Gemini (tentativo {tentativo+1}): {e}", flush=True)
            time.sleep(10)
    return None




def valida(ai, cache, m):
    rc = [norm(x["name"]) for x in cache.get(str(m["homeTeam"]["id"]), {}).get("squad", [])]
    rt = [norm(x["name"]) for x in cache.get(str(m["awayTeam"]["id"]), {}).get("squad", [])]
    ai["rosa_verificata"] = bool(rc and rt)
    if rc and rt:
        f = ai.get("formazioni") or {}
        for lato, r in (("casa", rc), ("trasferta", rt)):
            if lato in f:
                f[lato]["undici"] = [n for n in f[lato].get("undici", []) if ok(n, r)]
        for k in ("possibili_marcatori", "possibili_ammoniti"):
            ai[k] = [x for x in ai.get(k, []) if ok(x.get("giocatore"), rc if x.get("squadra") == "casa" else rt)]
    for k in ("stemma_casa", "stemma_trasf"):
        s = ai.get(k) or {}
        s["colori"] = [c for c in s.get("colori", []) if re.fullmatch(r"#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?", str(c))][:2]
        s["pattern"] = s.get("pattern") if s.get("pattern") in PATTERN else "solid"
        ai[k] = s
    pp = ai.get("pronostico_principale") or {}
    if not isinstance(pp.get("probabilita"), (int, float)) or not pp.get("esito"):  # calcolo statistico di riserva
        k = {**(ai.get("prob_1x2") or {}), **(ai.get("mercati_completi") or {})}
        if k:
            e, v = max(k.items(), key=lambda x: x[1])
            nome = {"1": "Esito 1", "X": "Esito X", "2": "Esito 2", "GG": "Gol", "NG": "NoGol"}.get(e) or \
                re.sub(r"([UO])(?=\d)", lambda x: "Under " if x.group(1) == "U" else "Over ", e)
            pp = {"esito": nome, "probabilita": int(v), "motivazione_breve": "Mercato con la probabilita statistica piu alta"}
    if pp:
        pp["motivazione_breve"] = str(pp.get("motivazione_breve", ""))[:90]
        ai["pronostico_principale"] = pp
    return pulisci(ai)


def main():
    modello = scegli_modello(); print("Modello:", modello)
    try:
        vecchi = {m["id"]: m for m in json.load(open(OUT, encoding="utf-8")).get("matches", [])}
    except Exception:
        vecchi = {}
    tutte = partite()
    CH = ("analisi", "formazioni", "prob_1x2", "mercati_completi", "possibili_marcatori", "possibili_ammoniti",
          "pronostico_principale", "affidabilita", "stemma_casa", "stemma_trasf", "rosa_verificata")
    da_fare = [m for m in tutte if not vecchi.get(m["id"], {}).get("analisi") and m["status"] in ("TIMED", "SCHEDULED")
               and m["homeTeam"].get("id") and m["awayTeam"].get("id")]
    cache = carica_rose({t for m in da_fare for t in (m["homeTeam"]["id"], m["awayTeam"]["id"])})
    cl = classifiche({m["_c"] for m in da_fare})
    out = []
    for m in tutte:
        old = vecchi.get(m["id"], {})
        ft = (m.get("score") or {}).get("fullTime") or {}
        rec = {"id": m["id"], "comp": m["_c"], "compNome": COMP[m["_c"]], "data": m["utcDate"],
               "casa": m["homeTeam"]["name"], "trasf": m["awayTeam"]["name"], "stato": m["status"],
               "score": [ft.get("home"), ft.get("away")] if ft.get("home") is not None else None}
        ai = {k: old[k] for k in CH if k in old}
        if m in da_fare:
            r = analizza(modello, m, cache, cl)
            ai = valida(r, cache, m) if r else {}
            time.sleep(PAUSA)
        rec.update(ai); out.append(rec)
    out.sort(key=lambda x: x["data"])
    json.dump({"aggiornato_il": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z", "modello": modello, "matches": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Partite salvate:", len(out))


if __name__ == "__main__":
    main()
