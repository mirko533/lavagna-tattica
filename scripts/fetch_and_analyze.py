
#!/usr/bin/env python3
"""Scarica le partite dei prossimi 4 giorni e le analizza in batch con Gemini."""

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
    "BSA": "Brasileirão",
    "WC": "Mondiali",
    "EC": "Europei",
}

API = "https://api.football-data.org/v4"

USCITA = (
    Path(__file__).resolve().parent.parent
    / "public"
    / "data"
    / "matches.json"
)

GIORNI = 4

# Football-Data.org: pausa tra richieste API.
PAUSA_FOOTBALL = 5

# Gemini: massimo 10 partite per richiesta.
DIMENSIONE_BATCH = 4
PAUSA_GEMINI = 4
TIMEOUT_GEMINI = 60_000  # millisecondi per Google GenAI SDK

MODELLO_PRINCIPALE = "gemini-3.5-flash-lite"
MODELLO_FALLBACK = "gemini-3-flash-preview"

API_VERSION_GEMINI = "v1beta"

VIETATI = re.compile(
    r"\b(quote|scommess\w*|bookmaker|puntat\w*|schedin\w*|bet(?:ting|s)?)\b",
    re.I,
)

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

_ultimo = {
    "football": 0.0,
    "gemini": 0.0,
}


# ============================================================
# FUNZIONI GENERALI
# ============================================================

def attendi(chiave, pausa):
    """Rispetta la pausa minima tra chiamate dello stesso servizio."""
    trascorso = time.monotonic() - _ultimo.get(chiave, 0.0)

    if trascorso < pausa:
        time.sleep(pausa - trascorso)

    _ultimo[chiave] = time.monotonic()


def estrai_json(testo):
    """Estrae un JSON anche se Gemini aggiunge accidentalmente delimitatori."""
    testo = (testo or "").strip()

    if testo.startswith("```"):
        testo = re.sub(r"^```(?:json)?\s*", "", testo, flags=re.I)
        testo = re.sub(r"\s*```$", "", testo)

    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        pass

    inizio_array = testo.find("[")
    fine_array = testo.rfind("]")

    if inizio_array >= 0 and fine_array > inizio_array:
        return json.loads(testo[inizio_array:fine_array + 1])

    inizio_oggetto = testo.find("{")
    fine_oggetto = testo.rfind("}")

    if inizio_oggetto >= 0 and fine_oggetto > inizio_oggetto:
        return json.loads(testo[inizio_oggetto:fine_oggetto + 1])

    raise ValueError("La risposta Gemini non contiene JSON valido.")


def num(valore):
    """Converte un valore numerico, anche se contiene una percentuale."""
    if isinstance(valore, (int, float)):
        return float(valore)

    match = re.search(r"-?\d+(?:[.,]\d+)?", str(valore))

    if not match:
        return 0.0

    return float(match.group().replace(",", "."))


def a100(valori):
    """Normalizza una lista di valori affinché la somma sia 100."""
    valori = [max(0.0, float(v)) for v in valori]
    somma = sum(valori)

    if somma <= 0:
        return [round(100 / len(valori))] * len(valori)

    risultati = [round(v * 100 / somma) for v in valori]
    risultati[0] += 100 - sum(risultati)

    return risultati


def percentuale(valore):
    return max(0, min(100, round(num(valore))))


def colori(valori):
    if not isinstance(valori, list):
        valori = []

    valori = valori + [None, None]

    return [
        valore if isinstance(valore, str) and HEX.match(valore) else None
        for valore in valori[:2]
    ]


def formazione(valore):
    if not isinstance(valore, dict):
        valore = {}

    modulo = str(valore.get("modulo", "4-4-2")).strip()

    giocatori = valore.get("giocatori", [])

    if not isinstance(giocatori, list):
        giocatori = []

    giocatori = [
        str(giocatore).strip()[:40]
        for giocatore in giocatori[:11]
        if giocatore
    ]

    return {
        "modulo": modulo,
        "giocatori": giocatori,
    }


def normalizza_giocatori(valore):
    """Limita i possibili giocatori a due per squadra."""
    if not isinstance(valore, list):
        return []

    risultati = []

    for giocatore in valore[:2]:
        if isinstance(giocatore, str):
            giocatore = {"nome": giocatore}

        if not isinstance(giocatore, dict):
            continue

        nome = str(giocatore.get("nome", "")).strip()

        if not nome:
            continue

        risultati.append({
            "nome": nome[:80],
            "ruolo": str(giocatore.get("ruolo", ""))[:40],
            "probabilita": percentuale(
                giocatore.get("probabilita", 0)
            ),
            "motivazione": str(
                giocatore.get("motivazione", "")
            )[:180],
        })

    return risultati


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

def fd_get(percorso, chiave_api, **params):
    """Richiesta API con gestione del limite gratuito."""
    for tentativo in range(3):
        attendi("football", PAUSA_FOOTBALL)

        risposta = requests.get(
            API + percorso,
            headers={"X-Auth-Token": chiave_api},
            params=params,
            timeout=30,
        )

        if risposta.status_code == 429:
            print(
                "Limite Football-Data raggiunto. Attendo 60 secondi...",
                file=sys.stderr,
            )
            time.sleep(60)
            continue

        risposta.raise_for_status()

        return risposta.json()

    raise RuntimeError(
        f"Troppe richieste Football-Data: {percorso}"
    )


def classifica(codice, chiave_api):
    """Recupera la classifica disponibile di un campionato."""
    try:
        dati = fd_get(
            f"/competitions/{codice}/standings",
            chiave_api,
        )
    except Exception as errore:
        print(
            f"Classifica {codice} non disponibile: {errore}",
            file=sys.stderr,
        )
        return {}

    risultato = {}

    for gruppo in dati.get("standings", []):
        if gruppo.get("type") != "TOTAL":
            continue

        for riga in gruppo.get("table", []):
            squadra = riga.get("team", {})
            squadra_id = squadra.get("id")

            if squadra_id is None:
                continue

            risultato[squadra_id] = {
                "posizione": riga.get("position"),
                "punti": riga.get("points"),
                "giocate": riga.get("playedGames"),
                "forma": riga.get("form"),
            }

    return risultato


def squadra(dati, classifiche):
    nome = (
        dati.get("shortName")
        or dati.get("name")
        or "?"
    )

    return {
        "nome": nome,
        "sigla": dati.get("tla") or nome[:3].upper(),
        "colori": [None, None],
        "classifica": classifiche.get(dati.get("id")),
    }


def marcatori_reali(match):
    """
    Conserva esclusivamente gli eventi gol effettivamente
    restituiti da Football-Data.org.
    """
    risultati = []

    for evento in match.get("goals", []) or []:
        marcatore = evento.get("scorer") or {}

        nome = (
            marcatore.get("name")
            or marcatore.get("lastName")
            or ""
        )

        if not nome:
            continue

        minuto = evento.get("minute")
        recupero = evento.get("injuryTime")

        risultato = {
            "marcatore": nome,
            "minuto": minuto,
            "recupero": recupero,
            "squadra_id": evento.get("team", {}).get("id"),
        }

        assist = evento.get("assist")

        if assist:
            risultato["assist"] = (
                assist.get("name")
                or assist.get("lastName")
                or ""
            )

        score = evento.get("score")

        if isinstance(score, dict):
            risultato["risultato"] = (
                f"{score.get('home', '')}-{score.get('away', '')}"
            )

        risultati.append(risultato)

    return risultati


def risultato_reale(match):
    score = match.get("score") or {}

    full_time = (
        score.get("fullTime")
        or score.get("regularTime")
        or {}
    )

    return {
        "home": full_time.get("home"),
        "away": full_time.get("away"),
    }


# ============================================================
# NORMALIZZAZIONE ANALISI GEMINI
# ============================================================

def normalizza_analisi(dati):
    """Converte l'analisi Gemini nel formato usato dal frontend."""

    probabilita = dati.get("probabilita_1x2") or {}

    p1, px, p2 = a100([
        num(probabilita.get("1")),
        num(probabilita.get("X")),
        num(probabilita.get("2")),
    ])

    gol = dati.get("probabilita_gol") or {}

    over, under = a100([
        num(gol.get("over_2_5")),
        num(gol.get("under_2_5")),
    ])

    gol_si, gol_no = a100([
        num(gol.get("gol")),
        num(gol.get("nogol")),
    ])

    marcatori = dati.get("possibili_marcatori") or {}
    ammoniti = dati.get("possibili_ammoniti") or {}

    mercati = dati.get("mercati_completi") or {}

    mercati_normalizzati = {}

    if isinstance(mercati, dict):
        for nome, valore in mercati.items():
            if isinstance(valore, (int, float, str)):
                mercati_normalizzati[str(nome)[:60]] = percentuale(valore)

    # Garantisce la presenza dei mercati principali.
    mercati_normalizzati.setdefault("1", p1)
    mercati_normalizzati.setdefault("X", px)
    mercati_normalizzati.setdefault("2", p2)
    mercati_normalizzati.setdefault("1X", min(100, p1 + px))
    mercati_normalizzati.setdefault("X2", min(100, px + p2))
    mercati_normalizzati.setdefault("12", min(100, p1 + p2))
    mercati_normalizzati.setdefault("GG", gol_si)
    mercati_normalizzati.setdefault("NG", gol_no)
    mercati_normalizzati.setdefault("Over 2.5", over)
    mercati_normalizzati.setdefault("Under 2.5", under)

    return {
        "analisi_tattica": str(
            dati.get("analisi_tattica", "")
        )[:450],

        "probabilita_1x2": {
            "1": p1,
            "X": px,
            "2": p2,
        },

        "probabilita_gol": {
            "over_2_5": over,
            "under_2_5": under,
            "gol": gol_si,
            "nogol": gol_no,
        },

        "mercati_completi": mercati_normalizzati,

        "probabile_formazione_casa": formazione(
            dati.get("probabile_formazione_casa")
        ),

        "probabile_formazione_trasferta": formazione(
            dati.get("probabile_formazione_trasferta")
        ),

        "possibili_marcatori": {
            "casa": normalizza_giocatori(
                marcatori.get("casa")
            ),
            "trasferta": normalizza_giocatori(
                marcatori.get("trasferta")
            ),
        },

        "possibili_ammoniti": {
            "casa": normalizza_giocatori(
                ammoniti.get("casa")
            ),
            "trasferta": normalizza_giocatori(
                ammoniti.get("trasferta")
            ),
        },

        "consiglio_tecnico": str(
            dati.get("consiglio_tecnico", "")
        )[:500],

        "colori_casa": colori(
            dati.get("colori_casa")
        ),

        "colori_trasferta": colori(
            dati.get("colori_trasferta")
        ),
    }


# ============================================================
# PROMPT BATCH GEMINI
# ============================================================

def descrizione_squadra(sq):
    classifica_dati = sq.get("classifica")

    descrizione = sq.get("nome", "?")

    if classifica_dati:
        descrizione += (
            f" (posizione {classifica_dati.get('posizione')}, "
            f"{classifica_dati.get('punti')} punti, "
            f"{classifica_dati.get('giocate')} gare, "
            f"forma {classifica_dati.get('forma') or 'n.d.'})"
        )

    return descrizione


def prompt_batch(partite):
    """Costruisce un'unica richiesta contenente fino a 10 partite."""

    elenco = []

    for partita in partite:
        elenco.append({
            "id": partita["id"],
            "competizione": partita["competizione"]["nome"],
            "data": partita["ora_utc"][:10],
            "casa": descrizione_squadra(
                partita["squadra_casa"]
            ),
            "trasferta": descrizione_squadra(
                partita["squadra_trasferta"]
            ),
        })

    partite_json = json.dumps(
        elenco,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
Sei un analista calcistico professionista.

Analizza tutte le partite presenti nell'elenco.
Scrivi esclusivamente in italiano, con linguaggio statistico,
tecnico e prudente.

Non usare termini legati a scommesse, quote, bookmaker
o gioco d'azzardo.

DATI DELLE PARTITE:
{partite_json}

REGOLE IMPORTANTI:
- Restituisci un array JSON con un oggetto per ogni partita.
- Ogni oggetto deve contenere il campo "id" identico a quello ricevuto.
- Non omettere nessuna partita.
- Non inventare dati certi su giocatori o formazioni.
- Le formazioni sono stime e devono essere indicate come tali.
- Indica al massimo 2 possibili marcatori per squadra.
- Indica al massimo 2 possibili ammoniti per squadra.
- Le probabilità devono essere numeri interi da 0 a 100.
- Le probabilità 1, X e 2 devono sommare 100.
- Over 2.5 e Under 2.5 devono sommare 100.
- GG e NG devono sommare 100.
- I colori delle squadre devono essere codici esadecimali.
- Se un dato non è sufficientemente noto, usa una stima prudente.

STRUTTURA OBBLIGATORIA DI OGNI OGGETTO:

{{
  "id": 123456,
  "analisi_tattica": "Breve analisi tattica della partita.",
  "probabilita_1x2": {{
    "1": 45,
    "X": 28,
    "2": 27
  }},
  "probabilita_gol": {{
    "over_2_5": 55,
    "under_2_5": 45,
    "gol": 58,
    "nogol": 42
  }},
  "mercati_completi": {{
    "1": 45,
    "X": 28,
    "2": 27,
    "1X": 73,
    "X2": 55,
    "12": 72,
    "GG": 58,
    "NG": 42,
    "Over 1.5": 78,
    "Under 1.5": 22,
    "Over 2.5": 55,
    "Under 2.5": 45,
    "Over 3.5": 31,
    "Under 3.5": 69,
    "Multigol 1-3": 72,
    "Multigol 2-4": 61,
    "1+Over 1.5": 54,
    "1X+GG": 42,
    "2+Under 3.5": 38
  }},
  "probabile_formazione_casa": {{
    "modulo": "4-3-3",
    "giocatori": [
      "Portiere",
      "Difensore 1",
      "Difensore 2",
      "Difensore 3",
      "Difensore 4",
      "Centrocampista 1",
      "Centrocampista 2",
      "Centrocampista 3",
      "Attaccante 1",
      "Attaccante 2",
      "Attaccante 3"
    ]
  }},
  "probabile_formazione_trasferta": {{
    "modulo": "4-4-2",
    "giocatori": [
      "Portiere",
      "Difensore 1",
      "Difensore 2",
      "Difensore 3",
      "Difensore 4",
      "Centrocampista 1",
      "Centrocampista 2",
      "Centrocampista 3",
      "Centrocampista 4",
      "Attaccante 1",
      "Attaccante 2"
    ]
  }},
  "possibili_marcatori": {{
    "casa": [
      {{
        "nome": "Nome giocatore",
        "ruolo": "Attaccante",
        "probabilita": 35,
        "motivazione": "Motivazione sintetica."
      }}
    ],
    "trasferta": [
      {{
        "nome": "Nome giocatore",
        "ruolo": "Attaccante",
        "probabilita": 25,
        "motivazione": "Motivazione sintetica."
      }}
    ]
  }},
  "possibili_ammoniti": {{
    "casa": [
      {{
        "nome": "Nome giocatore",
        "ruolo": "Difensore",
        "probabilita": 30,
        "motivazione": "Motivazione sintetica."
      }}
    ],
    "trasferta": [
      {{
        "nome": "Nome giocatore",
        "ruolo": "Centrocampista",
        "probabilita": 28,
        "motivazione": "Motivazione sintetica."
      }}
    ]
  }},
  "consiglio_tecnico": "Breve previsione statistica motivata.",
  "colori_casa": ["#0B3D91", "#FFFFFF"],
  "colori_trasferta": ["#CC0000", "#FFFFFF"]
}}

Restituisci SOLTANTO l'array JSON completo.
Nessun testo introduttivo, nessuna spiegazione esterna al JSON.
""".strip()


# ============================================================
# GEMINI: SOLO MODELLO PRINCIPALE E UNICO FALLBACK
# ============================================================

def crea_client(chiave):
    """Crea il client usando esplicitamente l'endpoint standard v1beta."""
    return genai.Client(
        api_key=chiave,
        http_options=types.HttpOptions(
            api_version=API_VERSION_GEMINI,
            timeout=TIMEOUT_GEMINI,
        ),
    )


def genera_batch(client, partite):
    """
    Invia un gruppo di partite con una sola richiesta Gemini.
    Usa il fallback esclusivamente se il modello principale fallisce.
    """

    prompt = prompt_batch(partite)

    modelli = [
        MODELLO_PRINCIPALE,
        MODELLO_FALLBACK,
    ]

    for indice, modello in enumerate(modelli):
        if indice > 0:
            print(
                f"  Uso fallback Gemini: {modello}",
                file=sys.stderr,
            )

        attendi("gemini", PAUSA_GEMINI)

        try:
            risposta = client.models.generate_content(
                model=modello,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )

            risultati = estrai_json(risposta.text)

            if isinstance(risultati, dict):
                risultati = [risultati]

            if not isinstance(risultati, list):
                raise ValueError(
                    "Gemini non ha restituito un array JSON."
                )

            # Indicizza i risultati usando l'ID della partita.
            indicizzati = {}

            for elemento in risultati:
                if not isinstance(elemento, dict):
                    continue

                partita_id = elemento.get("id")

                if partita_id is None:
                    continue

                if VIETATI.search(
                    json.dumps(elemento, ensure_ascii=False)
                ):
                    print(
                        f"  Risposta con termini non ammessi per ID {partita_id}.",
                        file=sys.stderr,
                    )
                    continue

                indicizzati[str(partita_id)] = elemento

            return indicizzati

        except Exception as errore:
            print(
                f"  Errore Gemini con {modello}: {str(errore)[:300]}",
                file=sys.stderr,
            )

            if indice == len(modelli) - 1:
                print(
                    "  Anche il modello fallback non ha risposto.",
                    file=sys.stderr,
                )

    return {}


# ============================================================
# CACHE
# ============================================================

def carica_cache(adesso):
    """Riutilizza le analisi valide delle ultime 48 ore."""
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
        analizzato_il = partita.get("analizzato_il")

        if not partita.get("analisi") or not analizzato_il:
            continue

        try:
            data_analisi = datetime.fromisoformat(
                analizzato_il.replace("Z", "+00:00")
            )

            if data_analisi.tzinfo is None:
                data_analisi = data_analisi.replace(
                    tzinfo=timezone.utc
                )

            if adesso - data_analisi < timedelta(hours=48):
                cache[str(partita["id"])] = partita

        except (ValueError, KeyError, TypeError):
            continue

    return cache


# ============================================================
# COSTRUZIONE PARTITE
# ============================================================

def crea_partita(match, classifiche, cache):
    partita_id = str(match["id"])
    codice = match["competition"]["code"]

    if partita_id in cache:
        precedente = cache[partita_id]

        # Aggiorna i dati dinamici senza perdere i colori
        # e le analisi già generate.
        precedente["stato"] = match.get("status")

        precedente["risultato_reale"] = risultato_reale(match)
        precedente["marcatori_reali"] = marcatori_reali(match)

        precedente["squadra_casa"]["classifica"] = classifiche[
            codice
        ].get(match["homeTeam"].get("id"))

        precedente["squadra_trasferta"]["classifica"] = classifiche[
            codice
        ].get(match["awayTeam"].get("id"))

        return precedente

    return {
        "id": match["id"],

        "competizione": {
            "codice": codice,
            "nome": COMPETIZIONI[codice],
        },

        "ora_utc": match["utcDate"],
        "stato": match.get("status"),
        "giornata": match.get("matchday"),

        "risultato_reale": risultato_reale(match),
        "marcatori_reali": marcatori_reali(match),

        "squadra_casa": squadra(
            match["homeTeam"],
            classifiche[codice],
        ),

        "squadra_trasferta": squadra(
            match["awayTeam"],
            classifiche[codice],
        ),

        "analisi": None,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    chiave_fd = os.environ.get("FOOTBALL_DATA_API_KEY")
    chiave_gem = os.environ.get("GEMINI_API_KEY")

    if not chiave_fd:
        sys.exit("Errore: FOOTBALL_DATA_API_KEY non configurata.")

    if not chiave_gem:
        sys.exit("Errore: GEMINI_API_KEY non configurata.")

    adesso = datetime.now(timezone.utc)
    oggi = adesso.date()
    fine = oggi + timedelta(days=GIORNI)

    print("=" * 60)
    print("PRONOSTICI352 - AGGIORNAMENTO PARTITE")
    print("=" * 60)
    print(f"Periodo: {oggi} - {fine}")
    print(f"Campionati configurati: {len(COMPETIZIONI)}")
    print(f"Modello Gemini: {MODELLO_PRINCIPALE}")
    print(f"Fallback: {MODELLO_FALLBACK}")
    print(f"Partite per batch: {DIMENSIONE_BATCH}")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. CACHE
    # --------------------------------------------------------

    cache = carica_cache(adesso)

    print(
        f"Analisi riutilizzabili dalla cache: {len(cache)}"
    )

    # --------------------------------------------------------
    # 2. DOWNLOAD PARTITE
    # --------------------------------------------------------

    dati = fd_get(
        "/matches",
        chiave_fd,
        competitions=",".join(COMPETIZIONI.keys()),
        dateFrom=oggi.isoformat(),
        dateTo=(fine + timedelta(days=1)).isoformat(),
    )

    grezze = sorted(
        (
            match
            for match in dati.get("matches", [])
            if oggi.isoformat() <= match["utcDate"][:10] <= fine.isoformat()
            and match.get("competition", {}).get("code") in COMPETIZIONI
            and match.get("status") not in (
                "CANCELLED",
                "POSTPONED",
                "SUSPENDED",
            )
        ),
        key=lambda match: match["utcDate"],
    )

    print(
        f"Partite trovate: {len(grezze)} "
        f"dal {oggi} al {fine}"
    )

    # --------------------------------------------------------
    # 3. CLASSIFICHE
    # --------------------------------------------------------

    codici_presenti = sorted({
        match["competition"]["code"]
        for match in grezze
    })

    classifiche = {}

    for codice in codici_presenti:
        print(f"Recupero classifica: {COMPETIZIONI[codice]}")
        classifiche[codice] = classifica(
            codice,
            chiave_fd,
        )

    # --------------------------------------------------------
    # 4. PREPARAZIONE PARTITE E CACHE
    # --------------------------------------------------------

    partite = [
        crea_partita(match, classifiche, cache)
        for match in grezze
    ]

    da_analizzare = [
        partita
        for partita in partite
        if not partita.get("analisi")
    ]

    print(
        f"Partite da analizzare con Gemini: {len(da_analizzare)}"
    )

    # --------------------------------------------------------
    # 5. CLIENT GEMINI
    # --------------------------------------------------------

    client = crea_client(chiave_gem)

    # --------------------------------------------------------
    # 6. ANALISI IN BATCH DA 10 PARTITE
    # --------------------------------------------------------

    gruppi = [
        da_analizzare[i:i + DIMENSIONE_BATCH]
        for i in range(0, len(da_analizzare), DIMENSIONE_BATCH)
    ]

    totale_gruppi = len(gruppi)

    for indice, gruppo in enumerate(gruppi, start=1):
        print()
        print(
            f"Batch {indice}/{totale_gruppi}: "
            f"{len(gruppo)} partite"
        )

        for partita in gruppo:
            print(
                "  - "
                f"{partita['squadra_casa']['nome']} - "
                f"{partita['squadra_trasferta']['nome']}"
            )

        risultati = genera_batch(client, gruppo)

        for partita in gruppo:
            partita_id = str(partita["id"])
            analisi_grezza = risultati.get(partita_id)

            if not analisi_grezza:
                print(
                    f"  Analisi non disponibile per ID {partita_id}",
                    file=sys.stderr,
                )
                continue

            try:
                analisi = normalizza_analisi(analisi_grezza)

                partita["squadra_casa"]["colori"] = (
                    analisi.pop("colori_casa")
                )

                partita["squadra_trasferta"]["colori"] = (
                    analisi.pop("colori_trasferta")
                )

                partita["analisi"] = analisi

                partita["analizzato_il"] = (
                    datetime.now(timezone.utc).isoformat()
                )

                print(
                    f"  OK: {partita['squadra_casa']['nome']} - "
                    f"{partita['squadra_trasferta']['nome']}"
                )

            except Exception as errore:
                print(
                    f"  Errore normalizzazione ID {partita_id}: "
                    f"{errore}",
                    file=sys.stderr,
                )

        # Pausa di 4 secondi tra un batch e il successivo.
        if indice < totale_gruppi:
            print(
                f"Pausa di {PAUSA_GEMINI} secondi prima del prossimo batch..."
            )
            time.sleep(PAUSA_GEMINI)

    # --------------------------------------------------------
    # 7. SALVATAGGIO JSON
    # --------------------------------------------------------

    USCITA.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "data": oggi.isoformat(),
        "fino_al": fine.isoformat(),
        "generato_il": datetime.now(timezone.utc).isoformat(),
        "esempio": False,
        "partite": partite,
    }

    USCITA.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    analizzate = sum(
        1 for partita in partite
        if partita.get("analisi")
    )

    print()
    print("=" * 60)
    print("AGGIORNAMENTO COMPLETATO")
    print(f"Partite totali: {len(partite)}")
    print(f"Partite analizzate: {analizzate}")
    print(f"Partite senza analisi: {len(partite) - analizzate}")
    print(f"File salvato: {USCITA}")
    print("=" * 60)


if __name__ == "__main__":
    main()
