import os
import json
import urllib.request
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
APP_URL = "https://" + "mirko533" + ".github.io/" + "lavagna-tattica/"

LABELS = {
    "1": "1 FISSO", "X": "PAREGGIO X", "2": "2 FISSO",
    "1X": "1X", "X2": "X2", "12": "12",
    "GG": "GOAL (GG)", "NG": "NOGOAL",
    "O1.5": "OVER 1.5", "U2.5": "UNDER 2.5", "O2.5": "OVER 2.5",
    "U3.5": "UNDER 3.5", "MG1-3": "MULTIGOL 1-3", "MG2-4": "MULTIGOL 2-4",
    "1X+O1.5": "1X + O1.5", "X2+O1.5": "X2 + O1.5"
}

def clean_team(name):
    for token in ["Club ", "FC ", "CF ", "AF ", "KV ", "FK ", "ŠK ", "SE ", "AC ", "ACF ", " FC", " CF", " KV", " FK"]:
        name = name.replace(token, "")
    return name.strip()

def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def generate_card(title, subtitle, selection, avg_prob, vip_mode=False, out_path="card.png"):
    W = 1080
    row_h = 115
    header_h = 250
    footer_h = 140
    H = header_h + (len(selection) * row_h) + footer_h

    if vip_mode:
        bg_color = (12, 10, 9)
        card_bg = (28, 25, 23)
        accent = (245, 158, 11)
        accent_light = (253, 224, 71)
        badge_bg = (120, 53, 15)
        badge_txt = (254, 240, 138)
    else:
        bg_color = (11, 17, 32)
        card_bg = (30, 41, 59)
        accent = (16, 185, 129)
        accent_light = (52, 211, 153)
        badge_bg = (6, 78, 59)
        badge_txt = (167, 243, 208)

    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([24, 24, W - 24, H - 24], radius=36, outline=accent, width=4)

    f_brand = get_font(48, bold=True)
    f_title = get_font(34, bold=True)
    f_sub = get_font(24, bold=False)
    f_match = get_font(30, bold=True)
    f_meta = get_font(22, bold=False)
    f_badge = get_font(26, bold=True)

    brand_txt = "352 PRONOSTICI  •  VIP GOLD" if vip_mode else "352 PRONOSTICI"
    draw.text((64, 56), brand_txt, fill=accent_light, font=f_brand)
    draw.text((64, 122), title, fill=(255, 255, 255), font=f_title)
    draw.text((64, 170), subtitle, fill=(148, 163, 184), font=f_sub)
    draw.line([(64, 220), (W - 64, 220)], fill=accent, width=3)

    y = header_h
    for idx, item in enumerate(selection, 1):
        draw.rounded_rectangle([56, y, W - 56, y + 96], radius=20, fill=card_bg, outline=(51, 65, 85), width=2)
        is_locked = vip_mode and idx > 3
        match_str = f"{idx}.  {item['casa']}  vs  {item['trasf']}"
        if len(match_str) > 34:
            match_str = match_str[:33] + "…"
        meta_str = f"{item['compNome']}  •  Ore {item['ora']}" if item['ora'] else item['compNome']

        draw.text((84, y + 18), match_str, fill=(255, 255, 255), font=f_match)
        draw.text((84, y + 58), meta_str, fill=(148, 163, 184), font=f_meta)

        if is_locked:
            b_text = "AREA VIP"
            b_fill = (69, 26, 3)
            t_fill = (251, 191, 36)
        else:
            b_text = f"{item['label']}  {item['prob']}%"
            b_fill = badge_bg
            t_fill = badge_txt

        draw.rounded_rectangle([W - 330, y + 22, W - 76, y + 74], radius=14, fill=b_fill, outline=accent, width=2)
        draw.text((W - 310, y + 33), b_text, fill=t_fill, font=f_badge)
        y += row_h

    draw.line([(64, y + 10), (W - 64, y + 10)], fill=(51, 65, 85), width=2)
    draw.text((64, y + 38), f"AFFIDABILITA MEDIA: {avg_prob}%", fill=accent_light, font=f_title)
    draw.text((64, y + 82), "Analisi complete su 352 Pronostici", fill=(148, 163, 184), font=f_sub)

    img.save(out_path, "PNG")
    return out_path
def send_photo_multipart(image_path, caption, vip_mode=False):
    if not BOT_TOKEN or not CHAT_ID:
        return

    boundary = "----WebKitFormBoundary352Pronostici"
    url = "https://" + "api.telegram.org" + "/bot" + BOT_TOKEN + "/sendPhoto"

    buttons = [[{"text": "📊 Apri App 352 Pronostici", "url": APP_URL}]]
    if vip_mode:
        buttons.append([{"text": "👑 Sblocca VIP / Lista d'Attesa (-20%)", "url": APP_URL}])

    reply_markup = json.dumps({"inline_keyboard": buttons})

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    parts = []
    for name, val in [("chat_id", CHAT_ID), ("caption", caption), ("parse_mode", "HTML"), ("reply_markup", reply_markup)]:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode("utf-8"))

    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"card.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8")
        + img_bytes + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req) as resp:
            print("Card grafica inviata con successo:", resp.status)
    except Exception as e:
        print("Errore invio card:", e)

def get_varied_trend(match, index):
    p1x2 = match.get("prob_1x2") or {}
    mc = match.get("mercati_completi") or {}
    groups = [
        ["1", "2", "1X+O1.5", "X2+O1.5"],
        ["O1.5", "O2.5", "GG", "MG2-4"],
        ["1X", "X2", "MG1-3", "U3.5"],
        ["1", "2", "GG", "O1.5"]
    ]
    preferred_keys = groups[index % len(groups)]
    best_k, best_v = None, 0
    for k in preferred_keys:
        val = p1x2.get(k) if k in p1x2 else mc.get(k, 0)
        if val and val > best_v:
            best_k, best_v = k, val
    if not best_k or best_v < 52:
        all_c = {**p1x2, **mc}
        if all_c:
            best_k = max(all_c, key=lambda x: all_c[x])
            best_v = all_c[best_k]
        else:
            return "DATI", 60
    return LABELS.get(best_k, best_k), int(best_v)

def format_time(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return ""

def main():
    path = "public/data/matches.json"
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    all_matches = raw.get("matches", [])
    timed = [m for m in all_matches if m.get("stato") == "TIMED"]
    pool = timed if timed else all_matches

    enriched = []
    for idx, m in enumerate(pool):
        label, prob = get_varied_trend(m, idx)
        enriched.append({
            "casa": clean_team(m.get("casa", "")),
            "trasf": clean_team(m.get("trasf", "")),
            "compNome": m.get("compNome", "Calcio"),
            "ora": format_time(m.get("data", "")),
            "label": label,
            "prob": prob
        })

    enriched.sort(key=lambda x: x["prob"], reverse=True)

    hour = datetime.now(timezone.utc).hour
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    oggi = datetime.now().strftime("%d/%m/%Y")

    if event_name == "schedule" and hour in (6, 7, 8):
        title = "SELEZIONE MATTUTINA  •  7 EVENTI"
        subtitle = f"Analisi statistica del {oggi}"
        selection = enriched[:7]
        vip_mode = False
    elif event_name == "schedule" and hour in (13, 14, 15):
        title = "ANALISI POMERIDIANA  •  8 EVENTI"
        subtitle = f"Combinazione matematica del {oggi}"
        selection = enriched[:8]
        vip_mode = False
    elif event_name == "schedule" and hour in (17, 18, 19):
        title = "MULTI-ANALISI SERALE  •  12 EVENTI"
        subtitle = f"Panoramica estesa del {oggi}"
        selection = enriched[:12]
        vip_mode = False
    elif event_name == "schedule" and hour in (21, 22, 23):
        title = "SELEZIONE ESCLUSIVA  •  TOP 6 VIP"
        subtitle = f"I migliori indici statistici • {oggi}"
        selection = enriched[:6]
        vip_mode = True
    else:
        title = "SELEZIONE DEL GIORNO  •  8 EVENTI"
        subtitle = f"Elaborazione algoritmo 352 • {oggi}"
        selection = enriched[:8]
        vip_mode = False

    if not selection:
        return

    avg_prob = round(sum(x["prob"] for x in selection) / len(selection))
    card_file = generate_card(title, subtitle, selection, avg_prob, vip_mode=vip_mode)
 

    if vip_mode:
        caption = (
            f"👑 <b>352 VIP GOLD — {title}</b>\n\n"
            f"✨ Ecco le nostre proposte esclusive di oggi basate sui migliori indici matematici! "
            f"3 analisi sono già in chiaro e 3 sono riservate ai membri del Club.\n\n"
            f"📲 <b>Visita l'app ufficiale</b> per leggere le analisi complete, le probabili formazioni e bloccare il tuo posto VIP con il <b>20% di sconto</b>! 👇"
        )
    else:
        caption = (
            f"⚽️ <b>352 PRONOSTICI — {title}</b>\n\n"
            f"🔥 Ecco le nostre proposte statistiche di oggi elaborate dall'algoritmo! "
            f"Affidabilità media della selezione: <b>{avg_prob}%</b> 📊\n\n"
            f"📲 <b>Visita l'app ufficiale</b> per consultare gratuitamente tutti i 28 mercati, gli xG e lo stato di forma delle squadre! 👇"
        )

    send_photo_multipart(card_file, caption, vip_mode=vip_mode)

if __name__ == "__main__":
    main()
