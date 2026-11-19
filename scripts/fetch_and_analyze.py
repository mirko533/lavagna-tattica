#!/usr/bin/env python3
"""Scarica le partite dei prossimi 7 giorni (Football-Data.org v4) e genera l'analisi con Gemini."""
import json, os, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from google import genai
from google.genai import types

COMPETIZIONI = {"SA": "Serie A", "PL": "Premier League", "PD": "La Liga",
                "BL1": "Bundesliga", "FL1": "Ligue 1", "CL": "Champions League"}
API = "https://api.football-data.org/v4"
USCITA = Path(__file__).resolve().parent.parent / "public" / "data" / "matches.json"
PAUSA = 7  # secondi tra una chiamata e l'altra: il limite gratuito è 10 richieste/minuto
GIORNI = 7  # finestra di ricerca: da oggi a oggi + 7 giorni

# Modelli Gemini: preferiti (stabili) e parole da escludere (immagini, audio, embedding...)
MODELLI_PREFERITI = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
ESCLUDI = ("image", "tts", "audio", "live", "embedding", "imagen", "veo", "vision", "robotics",
           "computer-use", "learnlm", "gemma", "aqa", "native-audio")

VIETATI = re.compile(r"\b(quote|scommess\w*|bookmaker|puntat\w*|schedin\w*|bet(?:ting|s)?)\b", re.I)
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_ultimo = {}


def attendi(chiave):
    trascorso = time.monotonic() - _ultimo.get(chiave, 0)
    if trascorso < PAUSA:
        time.sleep(PAUSA - trascorso)
    _ultimo[chiave] = time.monotonic()


def fd_get(percorso, chiave_api, **params):
    for _ in range(3):
        attendi("fd")
        r = requests.get(API + percorso, headers={"X-Auth-Token": chiave_api}, params=params, timeout=30)
        if r.status_code == 429:
            print("Limite raggiunto, attendo 60s...", file=sys.stderr)
            time.sleep(60)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Troppe richieste a {percorso}")


def classifica(codice, chiave_api):
    try:
        dati = fd_get(f"/competitions/{codice}/standings", chiave_api)
    except Exception as e:
        print(f"Classifica {codice} non disponibile: {e}", file=sys.stderr)
        return {}
    out = {}
    for gruppo in dati.get("standings", []):
        if gruppo.get("type") != "TOTAL":
            continue
        for riga in gruppo.get("table", []):
            out[riga["team"]["id"]] = {"posizione": riga.get("position"), "punti": riga.get("points"),
                                       "giocate": riga.get("playedGames"), "forma": riga.get("form")}
    return out


def scegli_modelli(client):
    """Restituisce i modelli Gemini che supportano generateContent, in ordine di preferenza."""
    forzato = os.environ.get("GEMINI_MODEL", "").strip()
    disponibili = []
    try:
        for m in client.models.list():
            azioni = getattr(m, "supported_actions", None) or []
            nome = (m.name or "").removeprefix("models/")
            if "generateContent" in azioni and nome.startswith("gemini") \
                    and not any(x in nome for x in ESCLUDI):
                disponibili.append(nome)
    except Exception as e:
        print(f"Elenco modelli non disponibile ({e}), uso i preferiti.", file=sys.stderr)
        disponibili = list(MODELLI_PREFERITI)

    ordinati = [n for n in MODELLI_PREFERITI if n in disponibili]
    ordinati += [n for n in disponibili if n not in ordinati and "flash" in n]
    ordinati += [n for n in disponibili if n not in ordinati]
    if forzato:
        ordinati = [forzato] + [n for n in ordinati if n != forzato]
    if not ordinati:
        sys.exit("Nessun modello Gemini con generateContent disponibile per questa chiave API.")
    print("Modelli candidati:", ", ".join(ordinati[:5]))
    return ordinati


def num(x):
    m = re.search(r"\d+(?:[.,]\d+)?", str(x))
    return float(m.group().replace(",", ".")) if m else 0.0


def a100(valori):
    somma = sum(valori) or 1
    r = [round(v * 100 / somma) for v in valori]
    r[0] += 100 - sum(r)
    return r


def formazione(f):
    f = f if isinstance(f, dict) else {}
    modulo = str(f.get("modulo", "4-4-2")).strip()
    giocatori = [str(g)[:40] for g in f.get("giocatori", [])][:11]
    return {"modulo": modulo, "giocatori": giocatori}


def colori(c):
    c = c if isinstance(c, list) else []
    return [x if isinstance(x, str) and HEX.match(x) else None for x in (c + [None, None])[:2]]


def normalizza(d):
    p1, px, p2 = a100([num(d["probabilita_1x2"].get(k)) for k in ("1", "X", "2")])
    g = d["probabilita_gol"]
    over, under = a100([num(g.get("over_2_5")), num(g.get("under_2_5"))])
    gol, nogol = a100([num(g.get("gol")), num(g.get("nogol"))])
    return {
        "analisi_tattica": str(d["analisi_tattica"])[:450],
        "probabilita_1x2": {"1": p1, "X": px, "2": p2},
        "probabilita_gol": {"over_2_5": over, "under_2_5": under, "gol": gol, "nogol": nogol},
        "probabile_formazione_casa": formazione(d.get("probabile_formazione_casa")),
        "probabile_formazione_trasferta": formazione(d.get("probabile_formazione_trasferta")),
        "consiglio_tecnico": str(d["consiglio_tecnico"])[:500],
        "colori_casa": colori(d.get("colori_casa")),
        "colori_trasferta": colori(d.get("colori_trasferta")),
    }


def prompt_partita(p):
    def riga(sq):
        c = sq.get("classifica")
        return f"{sq['nome']}" + (f" (posizione {c['posizione']}, {c['punti']} punti in {c['giocate']} gare, forma {c.get('forma') or 'n.d.'})" if c else "")
    return f"""Sei un analista calcistico. Scrivi in italiano, solo con linguaggio statistico e analitico.
Non usare MAI termini legati a scommesse, quote, bookmaker o gioco d'azzardo.

Partita: {riga(p['squadra_casa'])} (casa) contro {riga(p['squadra_trasferta'])} (trasferta)
Competizione: {p['competizione']['nome']} - data {p['ora_utc'][:10]}

Restituisci SOLO un oggetto JSON con queste chiavi:
- "analisi_tattica": stringa di massimo 3 righe
- "probabilita_1x2": {{"1": int, "X": int, "2": int}} (somma 100)
- "probabilita_gol": {{"over_2_5": int, "under_2_5": int, "gol": int, "nogol": int}} (over+under=100, gol+nogol=100)
- "probabile_formazione_casa": {{"modulo": "4-3-3", "giocatori": [11 cognomi: portiere, poi difensori, centrocampisti, attaccanti]}}
- "probabile_formazione_trasferta": stessa struttura
- "consiglio_tecnico": la previsione statistica motivata in 2-3 frasi
- "colori_casa": [colore primario hex, colore secondario hex] della squadra di casa (es. "#0B3D91")
- "colori_trasferta": idem per la trasferta
Stima gli 11 titolari in base alle rose attuali, al meglio delle tue conoscenze."""


def analizza(client, modelli, partita):
    """Prova i modelli in ordine: se uno risponde 404 passa al successivo."""
    prompt = prompt_partita(partita)
    tentativi = 0
    while modelli and tentativi < 3 + len(modelli):
        tentativi += 1
        attendi("gemini")
        try:
            r = client.models.generate_content(
                model=modelli[0], contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3))
            d = json.loads(r.text)
            if isinstance(d, list):
                d = d[0]
            if VIETATI.search(json.dumps(d, ensure_ascii=False)):
                prompt += "\nATTENZIONE: la risposta precedente conteneva termini vietati. Riscrivila senza."
                continue
            return normalizza(d)
        except Exception as e:
            msg = str(e)
            print(f"  tentativo {tentativi} fallito ({modelli[0]}): {msg[:200]}", file=sys.stderr)
            if "404" in msg or "NOT_FOUND" in msg:
                scartato = modelli.pop(0)
                print(f"  modello {scartato} non utilizzabile, passo al successivo", file=sys.stderr)
            elif "429" in msg:
                time.sleep(40)
    return None


def squadra(t, classifiche):
    nome = t.get("shortName") or t.get("name") or "?"
    return {"nome": nome, "sigla": t.get("tla") or nome[:3].upper(), "colori": [None, None],
            "classifica": classifiche.get(t.get("id"))}


def main():
    chiave_fd, chiave_gem = os.environ["FOOTBALL_DATA_API_KEY"], os.environ["GEMINI_API_KEY"]
    adesso = datetime.now(timezone.utc)
    oggi = adesso.date()
    fine = oggi + timedelta(days=GIORNI)

    # Riusa le analisi già fatte nelle ultime 48 ore (risparmia richieste a Gemini)
    cache = {}
    if USCITA.exists():
        try:
            vecchio = json.loads(USCITA.read_text(encoding="utf-8"))
        except ValueError:
            vecchio = {}
        if not vecchio.get("esempio"):
            for p in vecchio.get("partite", []):
                t = p.get("analizzato_il")
                if p.get("analisi") and t and adesso - datetime.fromisoformat(t) < timedelta(hours=48):
                    cache[p["id"]] = p

    # dateTo viene richiesto con un giorno in più e poi filtrato, per non perdere l'ultimo giorno
    dati = fd_get("/matches", chiave_fd, competitions=",".join(COMPETIZIONI),
                  dateFrom=oggi.isoformat(), dateTo=(fine + timedelta(days=1)).isoformat())
    grezze = sorted((m for m in dati.get("matches", [])
                     if oggi.isoformat() <= m["utcDate"][:10] <= fine.isoformat()
                     and m["competition"]["code"] in COMPETIZIONI
                     and m.get("status") not in ("CANCELLED", "POSTPONED", "SUSPENDED")),
                    key=lambda m: m["utcDate"])
    print(f"{len(grezze)} partite trovate dal {oggi} al {fine}")

    classifiche = {c: classifica(c, chiave_fd) for c in sorted({m["competition"]["code"] for m in grezze})}

    # Client predefinito: nessuna api_version forzata (usa v1beta)
    client = genai.Client(api_key=chiave_gem)
    modelli = scegli_modelli(client)

    partite = []
    for n, m in enumerate(grezze, 1):
        if m["id"] in cache:
            partite.append(cache[m["id"]])
            continue
        cod = m["competition"]["code"]
        p = {"id": m["id"], "competizione": {"codice": cod, "nome": COMPETIZIONI[cod]},
             "ora_utc": m["utcDate"], "stato": m.get("status"), "giornata": m.get("matchday"),
             "squadra_casa": squadra(m["homeTeam"], classifiche[cod]),
             "squadra_trasferta": squadra(m["awayTeam"], classifiche[cod]), "analisi": None}
        print(f"[{n}/{len(grezze)}] Analizzo {p['squadra_casa']['nome']} - {p['squadra_trasferta']['nome']}")
        a = analizza(client, modelli, p)  # la pausa tra una partita e l'altra è gestita da attendi()
        if a:
            p["squadra_casa"]["colori"] = a.pop("colori_casa")
            p["squadra_trasferta"]["colori"] = a.pop("colori_trasferta")
            p["analisi"] = a
            p["analizzato_il"] = datetime.now(timezone.utc).isoformat()
        partite.append(p)

    USCITA.parent.mkdir(parents=True, exist_ok=True)
    USCITA.write_text(json.dumps({"data": oggi.isoformat(), "fino_al": fine.isoformat(),
                                  "generato_il": adesso.isoformat(), "esempio": False,
                                  "partite": partite}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
