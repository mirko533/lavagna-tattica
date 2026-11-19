
#!/usr/bin/env python3
"""
Pronostici352
Scarica le partite dei prossimi 4 giorni da Football-Data.org v4
e genera analisi statistiche tramite Gemini.

Timeline Live: utilizza esclusivamente risultati e marcatori
realmente restituiti dall'API Football-Data.org.
"""

import json
import os
import re
import sys
import time

from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from google import genai
from google.genai import types


# ============================================================
# CONFIGURAZIONE
# ============================================================

COMPETIZIONI = {
    "SA": "Serie A",
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "Champions League",
    "ELC": "Championship",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "BSA": "Serie A Brasile",
    "WC": "Mondiali FIFA",
    "EC": "Europei UEFA",
}

API = "https://api.football-data.org/v4"

USCITA = (
    Path(__file__).resolve().parent.parent
    / "public"
    / "data"
    / "matches.json"
)

PAUSA = 5
GIORNI = 4

MODELLI_PREFERITI = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
]

ESCLUDI = (
    "image",
    "tts",
    "audio",
    "live",
    "embedding",
    "imagen",
    "veo",
    "vision",
    "robotics",
    "computer-use",
    "learnlm",
    "gemma",
    "aqa",
    "native-audio",
)

VIETATI = re.compile(
    r"\b(quote|scommess\w*|bookmaker|puntat\w*|bet(?:ting|s)?)\b",
    re.I
)

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

_ultimo = {}


# ============================================================
# GESTIONE INTERVALLI E RICHIESTE API
# ============================================================

def attendi(chiave):
    trascorso = time.monotonic() - _ultimo.get(chiave, 0)

    if trascorso < PAUSA:
        time.sleep(PAUSA - trascorso)

    _ultimo[chiave] = time.monotonic()


def fd_get(percorso, chiave_api, **params):
    """
    Interroga Football-Data.org.
    Gestisce automaticamente il limite delle richieste.
    """

    for tentativo in range(4):

        attendi("fd")

        risposta = requests.get(
            API + percorso,
            headers={"X-Auth-Token": chiave_api},
            params=params,
            timeout=35
        )

        if risposta.status_code == 429:
            attesa = min(90, 20 * (tentativo + 1))

            print(
                f"Limite API raggiunto. Attendo {attesa} secondi...",
                file=sys.stderr
            )

            time.sleep(attesa)
            continue

        risposta.raise_for_status()

        return risposta.json()

    raise RuntimeError(
        f"Limite richieste Football-Data superato: {percorso}"
    )


# ============================================================
# CLASSIFICHE
# ============================================================

def classifica(codice, chiave_api):

    try:
        dati = fd_get(
            f"/competitions/{codice}/standings",
            chiave_api
        )

    except Exception as errore:

        print(
            f"Classifica {codice} non disponibile: {errore}",
            file=sys.stderr
        )

        return {}

    risultato = {}

    for gruppo in dati.get("standings", []):

        if gruppo.get("type") != "TOTAL":
            continue

        for riga in gruppo.get("table", []):

            risultato[riga["team"]["id"]] = {
                "posizione": riga.get("position"),
                "punti": riga.get("points"),
                "giocate": riga.get("playedGames"),
                "forma": riga.get("form"),
            }

    return risultato


# ============================================================
# SELEZIONE AUTOMATICA MODELLI GEMINI
# ============================================================

def scegli_modelli(client):

    forzato = os.environ.get("GEMINI_MODEL", "").strip()

    disponibili = []

    try:

        for modello in client.models.list():

            azioni = (
                getattr(modello, "supported_actions", None)
                or []
            )

            nome = (
                modello.name or ""
            ).removeprefix("models/")

            if (
                "generateContent" in azioni
                and nome.startswith("gemini")
                and not any(x in nome for x in ESCLUDI)
            ):
                disponibili.append(nome)

    except Exception as errore:

        print(
            f"Discovery modelli non disponibile: {errore}",
            file=sys.stderr
        )

        disponibili = list(MODELLI_PREFERITI)

    ordinati = [
        nome
        for nome in MODELLI_PREFERITI
        if nome in disponibili
    ]

    ordinati += [
        nome
        for nome in disponibili
        if nome not in ordinati and "flash" in nome
    ]

    ordinati += [
        nome
        for nome in disponibili
        if nome not in ordinati
    ]

    if forzato:

        ordinati = [
            forzato
        ] + [
            nome for nome in ordinati
            if nome != forzato
        ]

    if not ordinati:

        ordinati = list(MODELLI_PREFERITI)

    print(
        "Modelli Gemini candidati:",
        ", ".join(ordinati[:6])
    )

    return ordinati


# ============================================================
# NORMALIZZAZIONE DATI
# ============================================================

def num(valore):

    match = re.search(
        r"\d+(?:[.,]\d+)?",
        str(valore)
    )

    return (
        float(match.group().replace(",", "."))
        if match
        else 0.0
    )


def a100(valori):

    somma = sum(valori) or 1

    risultato = [
        round(v * 100 / somma)
        for v in valori
    ]

    risultato[0] += 100 - sum(risultato)

    return risultato


def formazione(f):

    f = f if isinstance(f, dict) else {}

    return {
        "modulo": str(
            f.get("modulo", "4-4-2")
        )[:12],

        "giocatori": [
            str(g)[:50]
            for g in f.get("giocatori", [])[:11]
        ],
    }


def colori(c):

    c = c if isinstance(c, list) else []

    return [
        x if isinstance(x, str) and HEX.match(x) else None
        for x in (c + [None, None])[:2]
    ]


def giocatori_stimati(elementi, con_motivazione=False):

    """
    Accetta esclusivamente nomi restituiti dal modello.
    Non genera mai nomi di giocatori inventati.
    """

    risultato = []

    if not isinstance(elementi, list):
        return risultato

    for elemento in elementi:

        if not isinstance(elemento, dict):
            continue

        nome = elemento.get("nome")

        if not nome:
            continue

        giocatore = {
            "nome": str(nome)[:70],

            "ruolo": str(
                elemento.get("ruolo", "n.d.")
            )[:30],

            "probabilita": max(
                0,
                min(
                    100,
                    round(num(elemento.get("probabilita")))
                )
            ),
        }

        if con_motivazione:

            giocatore["motivazione"] = str(
                elemento.get("motivazione", "")
            )[:180]

        risultato.append(giocatore)

    return risultato[:2]


def mercati_completi(d):

    chiavi = [
        "1X",
        "X2",
        "12",
        "GG",
        "NG",
        "Under 1.5",
        "Over 1.5",
        "Under 2.5",
        "Over 2.5",
        "Under 3.5",
        "Over 3.5",
        "Multigol 1-3",
        "Multigol 2-4",
        "1+Over 1.5",
        "1X+GG",
        "2+Under 3.5",
    ]

    fonte = d.get("mercati_completi", {})

    if not isinstance(fonte, dict):
        fonte = {}

    return {
        chiave: max(
            0,
            min(100, round(num(fonte.get(chiave))))
        )
        for chiave in chiavi
    }


def normalizza(d):

    probabilita = d.get("probabilita_1x2", {})
    gol_dati = d.get("probabilita_gol", {})

    p1, px, p2 = a100([
        num(probabilita.get("1")),
        num(probabilita.get("X")),
        num(probabilita.get("2")),
    ])

    over, under = a100([
        num(gol_dati.get("over_2_5")),
        num(gol_dati.get("under_2_5")),
    ])

    gol, nogol = a100([
        num(gol_dati.get("gol")),
        num(gol_dati.get("nogol")),
    ])

    marcatori = d.get("possibili_marcatori", {})
    ammoniti = d.get("possibili_ammoniti", {})

    if not isinstance(marcatori, dict):
        marcatori = {}

    if not isinstance(ammoniti, dict):
        ammoniti = {}

    return {

        "analisi_tattica": str(
            d.get("analisi_tattica", "")
        )[:450],

        "probabilita_1x2": {
            "1": p1,
            "X": px,
            "2": p2,
        },

        "probabilita_gol": {
            "over_2_5": over,
            "under_2_5": under,
            "gol": gol,
            "nogol": nogol,
        },

        "mercati_completi": mercati_completi(d),

        "probabile_formazione_casa": formazione(
            d.get("probabile_formazione_casa")
        ),

        "probabile_formazione_trasferta": formazione(
            d.get("probabile_formazione_trasferta")
        ),

        "possibili_marcatori": {

            "casa": giocatori_stimati(
                marcatori.get("casa")
            ),

            "trasferta": giocatori_stimati(
                marcatori.get("trasferta")
            ),
        },

        "possibili_ammoniti": {

            "casa": giocatori_stimati(
                ammoniti.get("casa"),
                True
            ),

            "trasferta": giocatori_stimati(
                ammoniti.get("trasferta"),
                True
            ),
        },

        "consiglio_tecnico": str(
            d.get("consiglio_tecnico", "")
        )[:500],

        "colori_casa": colori(
            d.get("colori_casa")
        ),

        "colori_trasferta": colori(
            d.get("colori_trasferta")
        ),
    }


# ============================================================
# DATI REALI PER LA TIMELINE LIVE
# ============================================================

def estrai_marcatori_reali(partita):

    """
    Estrae esclusivamente i marcatori presenti nel campo goals
    restituito realmente da Football-Data.org.

    Se l'API non restituisce marcatori, restituisce [].
    Non vengono creati eventi artificiali.
    """

    marcatori = []

    for evento in partita.get("goals") or []:

        marcatore = evento.get("scorer") or {}

        if not marcatore.get("name"):
            continue

        squadra = evento.get("team") or {}

        marcatori.append({

            "minuto": evento.get("minute"),

            "recupero": evento.get("injuryTime"),

            "squadra_id": squadra.get("id"),

            "squadra_nome": squadra.get("name"),

            "marcatore": marcatore.get("name"),

            "assist": (
                (evento.get("assist") or {}).get("name")
            ),

            "risultato": evento.get("score"),
        })

    return marcatori


def estrai_risultato_reale(partita):

    """
    Mantiene il risultato originale fornito dall'API.
    Nessun risultato viene calcolato o simulato.
    """

    return partita.get("score")


# ============================================================
# PROMPT GEMINI
# ============================================================

def prompt_partita(p):

    def riga(squadra):

        c = squadra.get("classifica")

        if not c:
            return squadra["nome"]

        return (
            f"{squadra['nome']} "
            f"(posizione {c['posizione']}, "
            f"{c['punti']} punti in {c['giocate']} gare, "
            f"forma {c.get('forma') or 'n.d.'})"
        )

    return f"""
Sei un analista calcistico professionale.

Scrivi esclusivamente in italiano, con linguaggio statistico,
tecnico e sportivo.

Non usare termini legati a gioco d'azzardo o attività di
scommessa.

Le probabilità sono stime statistiche, non certezze.

PARTITA:

{riga(p['squadra_casa'])} (casa)
contro
{riga(p['squadra_trasferta'])} (trasferta)

Competizione: {p['competizione']['nome']}
Data UTC: {p['ora_utc']}

Restituisci ESCLUSIVAMENTE un oggetto JSON valido.

STRUTTURA RICHIESTA:

1. analisi_tattica:
   Analisi tecnica sintetica della partita.

2. probabilita_1x2:
   {{"1": int, "X": int, "2": int}}
   Le tre percentuali devono sommare 100.

3. probabilita_gol:
   {{
     "over_2_5": int,
     "under_2_5": int,
     "gol": int,
     "nogol": int
   }}

4. mercati_completi:

   Restituisci probabilità intere da 0 a 100
   per tutte le seguenti chiavi:

   "1X"
   "X2"
   "12"
   "GG"
   "NG"
   "Under 1.5"
   "Over 1.5"
   "Under 2.5"
   "Over 2.5"
   "Under 3.5"
   "Over 3.5"
   "Multigol 1-3"
   "Multigol 2-4"
   "1+Over 1.5"
   "1X+GG"
   "2+Under 3.5"

5. probabile_formazione_casa:
   Oggetto con modulo e massimo 11 giocatori.

6. probabile_formazione_trasferta:
   Stessa struttura.

7. possibili_marcatori:

   {{
     "casa": [
       {{
         "nome": "Nome giocatore reale",
         "ruolo": "Attaccante",
         "probabilita": 35
       }}
     ],
     "trasferta": []
   }}

   Massimo 2 giocatori per squadra.
   Non inventare nomi.
   Se non hai informazioni sufficienti, restituisci [].

8. possibili_ammoniti:

   {{
     "casa": [
       {{
         "nome": "Nome giocatore reale",
         "ruolo": "Difensore",
         "probabilita": 40,
         "motivazione": "Motivazione tattica"
       }}
     ],
     "trasferta": []
   }}

   Massimo 2 giocatori per squadra.
   Non inventare nomi.

9. consiglio_tecnico:
   Sintesi statistica motivata.

10. colori_casa:
    Due colori HEX plausibili.

11. colori_trasferta:
    Due colori HEX plausibili.

IMPORTANTE:

Non dichiarare come ufficiali le formazioni non confermate.
Non inventare giocatori.
Non presentare le probabilità come garanzie.
"""


# ============================================================
# ANALISI GEMINI CON FALLBACK AUTOMATICO
# ============================================================

def analizza(client, modelli, partita):

    prompt = prompt_partita(partita)

    tentativi = 0

    while modelli and tentativi < 3 + len(modelli):

        tentativi += 1

        attendi("gemini")

        modello = modelli[0]

        try:

            risposta = client.models.generate_content(

                model=modello,

                contents=prompt,

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    temperature=0.25
                )
            )

            dati = json.loads(risposta.text)

            if isinstance(dati, list):
                dati = dati[0]

            if VIETATI.search(
                json.dumps(dati, ensure_ascii=False)
            ):

                prompt += (
                    "\nRiscrivi la risposta eliminando "
                    "qualsiasi termine non conforme."
                )

                continue

            return normalizza(dati)

        except Exception as errore:

            messaggio = str(errore)

            print(
                f"Gemini {modello}: {messaggio[:250]}",
                file=sys.stderr
            )

            if (
                "404" in messaggio
                or "NOT_FOUND" in messaggio
            ):

                scartato = modelli.pop(0)

                print(
                    f"Modello {scartato} non disponibile. "
                    "Provo il successivo.",
                    file=sys.stderr
                )

            elif "429" in messaggio:

                time.sleep(45)

            else:

                break

    return None


# ============================================================
# SQUADRE
# ============================================================

def squadra(t, classifiche):

    nome = (
        t.get("shortName")
        or t.get("name")
        or "?"
    )

    return {

        "nome": nome,

        "sigla": (
            t.get("tla")
            or nome[:3].upper()
        ),

        "colori": [
            None,
            None
        ],

        "classifica": classifiche.get(
            t.get("id")
        ),
    }


# ============================================================
# AGGIORNAMENTO CACHE
# ============================================================

def carica_cache(adesso):

    cache = {}

    if not USCITA.exists():
        return cache

    try:

        vecchio = json.loads(
            USCITA.read_text(encoding="utf-8")
        )

    except (ValueError, OSError):

        return cache

    if vecchio.get("esempio"):
        return cache

    for partita in vecchio.get("partite", []):

        timestamp = partita.get("analizzato_il")

        if not partita.get("analisi") or not timestamp:
            continue

        try:

            data_analisi = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

        except ValueError:

            continue

        if (
            adesso - data_analisi
            < timedelta(hours=48)
        ):

            cache[partita["id"]] = partita

    return cache


# ============================================================
# PROGRAMMA PRINCIPALE
# ============================================================

def main():

    chiave_fd = os.environ["FOOTBALL_DATA_API_KEY"]

    chiave_gem = os.environ["GEMINI_API_KEY"]

    adesso = datetime.now(timezone.utc)

    oggi = adesso.date()

    fine = oggi + timedelta(days=GIORNI)

    cache = carica_cache(adesso)

    print(
        f"Pronostici352: ricerca dal {oggi} al {fine}"
    )

    # Una sola interrogazione per tutte le competizioni.
    # Se il piano/API non consente una competizione,
    # l'API potrebbe rifiutare la richiesta: l'errore
    # viene mostrato senza inventare risultati.

    dati = fd_get(

        "/matches",

        chiave_fd,

        competitions=",".join(COMPETIZIONI.keys()),

        dateFrom=oggi.isoformat(),

        dateTo=fine.isoformat()
    )

    grezze = sorted(

        (
            partita
            for partita in dati.get("matches", [])

            if (
                oggi.isoformat()
                <= partita["utcDate"][:10]
                <= fine.isoformat()
            )

            and partita.get("competition", {}).get("code")
            in COMPETIZIONI

            and partita.get("status")
            not in (
                "CANCELLED",
                "POSTPONED",
                "SUSPENDED"
            )
        ),

        key=lambda partita: partita["utcDate"]
    )

    print(
        f"{len(grezze)} partite trovate."
    )

    codici = sorted({

        partita["competition"]["code"]

        for partita in grezze

    })

    classifiche = {

        codice: classifica(codice, chiave_fd)

        for codice in codici
    }

    # Il client Google GenAI utilizza l'endpoint v1beta
    # predefinito dell'SDK.

    client = genai.Client(
        api_key=chiave_gem
    )

    modelli = scegli_modelli(client)

    partite = []

    for numero_partita, m in enumerate(grezze, 1):

        codice = m["competition"]["code"]

        # Risultato e marcatori provengono sempre
        # dall'ultima risposta Football-Data.

        risultato_reale = estrai_risultato_reale(m)

        marcatori_reali = estrai_marcatori_reali(m)

        if m["id"] in cache:

            p = cache[m["id"]]

            # Aggiorna i dati live anche quando
            # l'analisi Gemini è già presente.

            p["stato"] = m.get("status")

            p["risultato_reale"] = risultato_reale

            p["marcatori_reali"] = marcatori_reali

            p["squadra_casa"] = squadra(
                m["homeTeam"],
                classifiche[codice]
            )

            p["squadra_trasferta"] = squadra(
                m["awayTeam"],
                classifiche[codice]
            )

            partite.append(p)

            print(
                f"[{numero_partita}/{len(grezze)}] "
                f"Cache aggiornata: "
                f"{m['homeTeam'].get('shortName')} - "
                f"{m['awayTeam'].get('shortName')}"
            )

            continue

        p = {

            "id": m["id"],

            "competizione": {

                "codice": codice,

                "nome": COMPETIZIONI[codice],
            },

            "ora_utc": m["utcDate"],

            "stato": m.get("status"),

            "giornata": m.get("matchday"),

            "risultato_reale": risultato_reale,

            "marcatori_reali": marcatori_reali,

            "squadra_casa": squadra(
                m["homeTeam"],
                classifiche[codigo] if False else classifiche[codice]
            ),

            "squadra_trasferta": squadra(
                m["awayTeam"],
                classifiche[codice]
            ),

            "analisi": None,
        }

        print(
            f"[{numero_partita}/{len(grezze)}] "
            f"Analizzo "
            f"{p['squadra_casa']['nome']} - "
            f"{p['squadra_trasferta']['nome']}"
        )

        analisi = analizza(
            client,
            modelli,
            p
        )

        if analisi:

            p["squadra_casa"]["colori"] = (
                analisi.pop("colori_casa")
            )

            p["squadra_trasferta"]["colori"] = (
                analisi.pop("colori_trasferta")
            )

            p["analisi"] = analisi

            p["analizzato_il"] = (
                datetime.now(timezone.utc).isoformat()
            )

        partite.append(p)

    # Salvataggio JSON.

    USCITA.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output = {

        "app": "Pronostici352",

        "data": oggi.isoformat(),

        "fino_al": fine.isoformat(),

        "giorni": GIORNI,

        "generato_il": datetime.now(
            timezone.utc
        ).isoformat(),

        "esempio": False,

        "partite": partite,
    }

    USCITA.write_text(

        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),

        encoding="utf-8"
    )

    print(
        f"Completato. Salvate {len(partite)} partite in {USCITA}"
    )


if __name__ == "__main__":
    main()
