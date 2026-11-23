import os
import json
import urllib.request
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
APP_URL = "https://github.io"
PHOTO_URL = "https://github.ioicon-512.png"

LABELS = {
    "1": "Esito 1", "X": "Esito X", "2": "Esito 2",
    "1X": "Doppia Chance 1X", "X2": "Doppia Chance X2", "12": "Doppia Chance 12",
    "GG": "Goal (GG)", "NG": "NoGoal (NG)",
    "O1.5": "Over 1.5 Gol", "U2.5": "Under 2.5 Gol", "O2.5": "Over 2.5 Gol",
    "U3.5": "Under 3.5 Gol", "MG1-3": "Multigol 1-3", "MG2-4": "Multigol 2-4",
    "1X+O1.5": "1X + Over 1.5", "X2+O1.5": "X2 + Over 1.5"
}

FLAG_MAP = {
    "SA": "🇮🇹", "PL": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "PD": "🇪🇸", "BL1": "🇩🇪", "FL1": "🇫🇷",
    "CL": "🇪🇺", "EL": "🇪🇺", "DED": "🇳🇱", "PPL": "🇵🇹", "ELC": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"
}

def send_telegram(text, with_photo=True):
    if not BOT_TOKEN or not CHAT_ID:
        print("Mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID nei Secrets.")
        return

    # Telegram limita le didascalie delle foto a 1024 caratteri; se il post da 12 eventi è più lungo, invia messaggio formattato
    if with_photo and len(text) <= 1000:
        url = f"https://telegram.org{BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": CHAT_ID,
            "photo": PHOTO_URL,
            "caption": text,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "📊 Apri App 352 Pronostici", "url": APP_URL}]
                ]
            }
        }
    else:
        url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "📊 Apri App 352 Pronostici", "url": APP_URL}],
                    [{"text": "💎 Accedi all'Area VIP", "url": APP_URL}]
                ]
            }
        }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            print("Messaggio inviato su Telegram con successo:", resp.status)
    except Exception as e:
        print("Errore invio Telegram:", e)

def get_best_trend(match):
    candidates = {}
    p1x2 = match.get("prob_1x2") or {}
    mc = match.get("mercati_completi") or {}

    for k in ["1", "X", "2"]:
        if k in p1x2:
            candidates[k] = p1x2[k]
    for k in ["1X", "X2", "12", "GG", "NG", "O1.5", "U2.5", "O2.5", "U3.5", "MG1-3", "MG2-4", "1X+O1.5", "X2+O1.5"]:
        if k in mc:
            candidates[k] = mc[k]

    if not candidates:
        return "Analisi Dati", 50

    best_key = max(candidates, key=lambda k: candidates[k])
    return LABELS.get(best_key, best_key), int(candidates[best_key])

def format_time(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return ""

def main():
    path = "public/data/matches.json"
    if not os.path.exists(path):
        print("File public/data/matches.json non trovato.")
        return

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    all_matches = raw.get("matches", [])
    timed_matches = [m for m in all_matches if m.get("stato") == "TIMED"]
    pool = timed_matches if timed_matches else all_matches

    if not pool:
        print("Nessuna partita disponibile.")
        return

    enriched = []
    for m in pool:
        label, prob = get_best_trend(m)
        enriched.append({
            "casa": m.get("casa", ""),
            "trasf": m.get("trasf", ""),
            "comp": m.get("comp", ""),
            "compNome": m.get("compNome", ""),
            "ora": format_time(m.get("data", "")),
            "label": label,
            "prob": prob
        })

    enriched.sort(key=lambda x: x["prob"], reverse=True)

    hour = datetime.now(timezone.utc).hour
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    # Selezione formato in base all'orario
    if event_name == "schedule" and hour in (6, 7, 8):
        title = "☀️ SELEZIONE MATTUTINA · 7 EVENTI"
        subtitle = "I 7 indicatori statistici più solidi elaborati oggi dal nostro algoritmo:"
        selection = enriched[:7]
        vip_mode = False
    elif event_name == "schedule" and hour in (13, 14, 15):
        title = "⚡ COMBINAZIONE POMERIDIANA · 8 EVENTI"
        subtitle = "Analisi multi-campionato su 8 match ad alta affidabilità matematica:"
        selection = enriched[:8]
        vip_mode = False
    elif event_name == "schedule" and hour in (17, 18, 19):
        title = "🌙 MULTI-ANALISI SERALE · 12 EVENTI"
        subtitle = "Panoramica completa su 12 sfide con i migliori trend statistici:"
        selection = enriched[:12]
        vip_mode = False
    elif event_name == "schedule" and hour in (21, 22, 23):
        title = "💎 ANTEPRIMA VIP · TOP 6 STATISTICI"
        subtitle = "I 6 match con l'indice matematico più alto in programma (3 sbloccabili in Area VIP):"
        selection = enriched[:6]
        vip_mode = True
    else:
        # Esecuzione manuale (Run workflow): pubblica selezione da 8 eventi
        title = "🔥 SELEZIONE STATISTICA DEL GIORNO · 8 EVENTI"
        subtitle = "Ecco gli 8 trend matematici più rilevanti elaborati dall'algoritmo 352:"
        selection = enriched[:8]
        vip_mode = False

    if not selection:
        return

    avg_prob = round(sum(x["prob"] for x in selection) / len(selection))

    lines = [
        f"⚽️ <b>352 PRONOSTICI — {title}</b>",
        f"<i>{subtitle}</i>\n"
    ]

    for idx, item in enumerate(selection, 1):
        flag = FLAG_MAP.get(item["comp"], "🏆")
        ora_txt = f" [{item['ora']}]" if item["ora"] else ""

        if vip_mode and idx > 3:
            lines.append(
                f"🔒 <b>{idx}. {flag} {item['casa']} - {item['trasf']}</b>{ora_txt}\n"
                f"   └ 🎯 Esito VIP: <tg-spoiler><b>{item['label']} ({item['prob']}%)</b></tg-spoiler> <i>(Sblocca su App)</i>"
            )
        else:
            lines.append(
                f"🔹 <b>{idx}. {flag} {item['casa']} - {item['trasf']}</b>{ora_txt}\n"
                f"   └ 📈 <b>{item['label']}</b> — Affidabilità: <b>{item['prob']}%</b>"
            )

    lines.append(f"\n📊 <b>Affidabilità Media Selezione: {avg_prob}%</b>")
    if vip_mode:
        lines.append("🔓 <i>Tocca gli spoiler qui sopra o entra nella sezione VIP dell'app per l'analisi completa!</i>")
    else:
        lines.append("👇 <i>Apri l'app per consultare xG, formazioni probabili e tutti i 28 mercati statistici:</i>")

    final_text = "\n".join(lines)
    # Usa la foto dell'app per i post compatti (7/8 eventi), e il layout esteso con doppio pulsante per i 12 eventi
    send_telegram(final_text, with_photo=(len(selection) <= 7))

if __name__ == "__main__":
    main()
