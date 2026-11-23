import os
import json
import glob
import urllib.request
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
APP_URL = "https://github.io"
PHOTO_URL = "https://github.ioicon-512.png"

def send_telegram_post(caption):
    if not BOT_TOKEN or not CHAT_ID:
        print("Mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID nei Secrets.")
        return

    url = f"https://telegram.org{BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": PHOTO_URL,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "📊 Apri Analisi Completa sull'App", "url": APP_URL}]
            ]
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            print("Post con foto inviato su Telegram:", resp.status)
    except Exception as e:
        print("Errore invio Telegram:", e)

def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    current_hour = datetime.now(timezone.utc).hour
    if event_name == "schedule" and current_hour not in (6, 7, 8):
        print("Non è l'orario del riepilogo mattutino, salto invio Telegram.")
        return

    matches = []
    for path in glob.glob("public/data/*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("matches", [])
                for m in items:
                    if isinstance(m, dict) and ("home" in m or "homeTeam" in m):
                        matches.append(m)
        except Exception:
            continue

    if not matches:
        print("Nessuna partita trovata nei JSON.")
        return

    matches.sort(key=lambda x: float(x.get("confidence", x.get("prob", 0)) or 0), reverse=True)
    top3 = matches[:3]

    lines = [
        "⚽️ <b>352 PRONOSTICI — ANALISI DEL GIORNO</b>",
        "<i>I 3 trend statistici più rilevanti rilevati oggi:</i>\n"
    ]

    for i, m in enumerate(top3, 1):
        home = m.get("home") or m.get("homeTeam", {}).get("name", "Casa")
        away = m.get("away") or m.get("awayTeam", {}).get("name", "Trasferta")
        league = m.get("league") or m.get("competition", "")
        pick = m.get("pick") or m.get("prediction") or m.get("tip", "Analisi disponibile")
        conf = m.get("confidence") or m.get("prob")

        row = f"<b>{i}. {home} vs {away}</b>"
        if league:
            row += f" ({league})"
        row += f"\n📈 Trend: <b>{pick}</b>"
        if conf:
            row += f" — Indice: <b>{conf}%</b>"
        lines.append(row + "\n")

    lines.append("👇 <i>Consulta medie gol, xG e statistiche complete:</i>")
    send_telegram_post("\n".join(lines))

if __name__ == "__main__":
    main()
