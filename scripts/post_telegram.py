#!/usr/bin/env python3
"""352 Pronostici - pubblicazione su Telegram (card immagine + pulsanti + riepilogo + sondaggio).

Variabili d'ambiente: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (secrets del repository).
Facoltative: FORCE_POST=1 per ripubblicare anche se lo slot di oggi risulta gia' inviato.
Font facoltativi in scripts/fonts/: Outfit-Bold.ttf, PlusJakartaSans-Bold.ttf, PlusJakartaSans-Regular.ttf
(font statici, scaricabili da Google Fonts). Senza di essi si usa DejaVu.
"""
import os
import re
import io
import json
import math
import uuid
import html
import time
import random
import unicodedata
import urllib.request
import urllib.error
from functools import lru_cache
from datetime import datetime, timezone, timedelta

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from zoneinfo import ZoneInfo
    ROME = ZoneInfo("Europe/Rome")
except Exception:  # fallback prudente se manca tzdata
    ROME = timezone(timedelta(hours=1))

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
APP_URL = "https://mirko533.github.io/lavagna-tattica/"
MATCHES_PATH = "public/data/matches.json"
STATE_PATH = "public/data/telegram_state.json"

GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

LABELS = {
    "1": "1 FISSO", "X": "PAREGGIO X", "2": "2 FISSO",
    "1X": "1X", "X2": "X2", "12": "12",
    "GG": "GOAL (GG)", "NG": "NOGOAL",
    "O1.5": "OVER 1.5", "U2.5": "UNDER 2.5", "O2.5": "OVER 2.5",
    "U3.5": "UNDER 3.5", "MG1-3": "MULTIGOL 1-3", "MG2-4": "MULTIGOL 2-4",
    "1X+O1.5": "1X + O1.5", "X2+O1.5": "X2 + O1.5",
}


def app_link(tab=None):
    """Link all'app con parametri di tracciamento; ?tab=vip apre direttamente la tab VIP."""
    q = "src=telegram" + (f"&tab={tab}" if tab else "")
    return f"{APP_URL}?{q}"


# ----------------------------------------------------------------------------
# Nomi squadra: abbreviazioni e pulizia
# ----------------------------------------------------------------------------
_STRIP = re.compile(
    r"\b(?:FC|CF|AFC|AC|ACF|AS|SS|SSC|US|SV|SK|KV|FK|SE|BC|CD|UD|RC|RCD|SC|Club|Calcio|ŠK)\b",
    re.IGNORECASE,
)
_NUMS = re.compile(r"\b\d{2,4}\b")
ABBR = {
    "internazionale milano": "Inter", "internazionale": "Inter", "hellas verona": "Verona",
    "manchester city": "Man City", "manchester united": "Man United",
    "tottenham hotspur": "Tottenham", "newcastle united": "Newcastle",
    "wolverhampton wanderers": "Wolves", "brighton & hove albion": "Brighton",
    "west ham united": "West Ham", "nottingham forest": "Nottm Forest",
    "leicester city": "Leicester", "leeds united": "Leeds", "crystal palace": "Palace",
    "atlético de madrid": "Atlético", "real sociedad de fútbol": "Real Sociedad",
    "real betis balompié": "Betis", "rayo vallecano de madrid": "Rayo Vallecano",
    "deportivo alavés": "Alavés", "borussia dortmund": "Dortmund", "bayer leverkusen": "Leverkusen",
    "bayern münchen": "Bayern", "borussia mönchengladbach": "M'gladbach",
    "eintracht frankfurt": "Francoforte", "paris saint-germain": "PSG",
    "olympique de marseille": "Marsiglia", "olympique lyonnais": "Lione",
    "sporting clube de portugal": "Sporting CP", "sl benfica": "Benfica", "tsg hoffenheim": "Hoffenheim",
}


def clean_team(name):
    n = _STRIP.sub(" ", str(name or ""))
    n = _NUMS.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip(" -.")
    return ABBR.get(n.casefold(), n) or str(name or "")


# ----------------------------------------------------------------------------
# Font e testo
# ----------------------------------------------------------------------------
_BASE = os.path.dirname(os.path.abspath(__file__))
_FD = os.path.join(_BASE, "fonts")
_DJ = "/usr/share/fonts/truetype/dejavu/"
_LB = "/usr/share/fonts/truetype/liberation/"


@lru_cache(maxsize=None)
def get_font(size, bold=False, heading=False):
    if heading:
        cands = [_FD + "/Outfit-Bold.ttf", _FD + "/PlusJakartaSans-Bold.ttf"]
    elif bold:
        cands = [_FD + "/PlusJakartaSans-Bold.ttf"]
    else:
        cands = [_FD + "/PlusJakartaSans-Regular.ttf"]
    cands += [_DJ + ("DejaVuSans-Bold.ttf" if (bold or heading) else "DejaVuSans.ttf"),
              _LB + ("LiberationSans-Bold.ttf" if (bold or heading) else "LiberationSans-Regular.ttf")]
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def fit_text(draw, text, size, max_w, bold=False, heading=False, min_size=16):
    """Riduce il corpo del testo finche' entra in max_w; se serve tronca con '…'."""
    text = str(text)
    s = size
    while s >= min_size:
        f = get_font(s, bold, heading)
        if draw.textlength(text, font=f) <= max_w:
            return text, f
        s -= 2
    f = get_font(min_size, bold, heading)
    while len(text) > 2 and draw.textlength(text + "…", font=f) > max_w:
        text = text[:-1]
    return text.rstrip() + "…", f


# ----------------------------------------------------------------------------
# Date (fuso Italia)
# ----------------------------------------------------------------------------
def parse_dt(iso):
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ROME)
    except Exception:
        return None


def fmt_when(dt):
    return f"{GIORNI[dt.weekday()]} {dt.day} {MESI[dt.month - 1]} · {dt:%H:%M}" if dt else ""


# ----------------------------------------------------------------------------
# Scudetti (colori sociali, niente loghi protetti)
# ----------------------------------------------------------------------------
_PAL = [(29, 78, 216), (185, 28, 28), (4, 120, 87), (124, 58, 237), (180, 83, 9), (14, 116, 144)]


def _hex(c):
    if isinstance(c, str) and re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", c):
        c = c[1:]
        if len(c) == 3:
            c = "".join(x * 2 for x in c)
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return None


def _lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return .2126 * r + .7152 * g + .0722 * b


def _bez(p0, p1, p2, p3, n=14):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        pts.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return pts


def _shield_pts():
    pts = [(3, 3), (37, 3), (37, 24)]
    pts += _bez((37, 24), (37, 35), (29, 41), (20, 44))
    pts += _bez((20, 44), (11, 41), (3, 35), (3, 24))
    return pts


def shield(name, st, w=40):
    """Scudetto RGBA largo w px (stessa grafica dell'app), disegnato 6x e ridotto per l'antialiasing."""
    S = 6
    st = st or {}
    cols = [x for x in (_hex(c) for c in (st.get("colori") or [])) if x]
    h = 0
    for ch in str(name):
        h = (h * 31 + ord(ch)) % 997
    c1 = cols[0] if cols else _PAL[h % 6]
    c2 = cols[1] if len(cols) > 1 else (248, 250, 252)
    pat = st.get("pattern") if st.get("pattern") in ("vertical", "horizontal", "diagonal", "half", "solid") else "solid"
    cen = _lum(c1) if pat == "solid" else (_lum(c1) + _lum(c2)) / 2 if pat == "half" else _lum(c2)
    tc = (11, 17, 32) if cen > .45 else (255, 255, 255)
    ascii_name = unicodedata.normalize("NFD", str(name))
    sig = re.sub(r"[^A-Za-z ]", "", ascii_name).strip()[:3].upper() or "?"
    cw, chh = 40 * S, 46 * S
    layer = Image.new("RGBA", (cw, chh), c1 + (255,))
    ld = ImageDraw.Draw(layer)
    sc = lambda pts: [(x * S, y * S) for x, y in pts]
    if pat == "vertical":
        ld.rectangle([14.3 * S, 0, 25.7 * S, chh], fill=c2)
    elif pat == "horizontal":
        ld.rectangle([0, 17 * S, cw, 31 * S], fill=c2)
    elif pat == "half":
        ld.rectangle([20 * S, 0, cw, chh], fill=c2)
    elif pat == "diagonal":
        ld.polygon(sc([(34, -4), (56, -4), (-4, 56), (-4, 34)]), fill=c2)
    ld.rectangle([0, 3 * S, cw, 11 * S], fill=(0, 0, 0, 30))
    mask = Image.new("L", (cw, chh), 0)
    ImageDraw.Draw(mask).polygon(sc(_shield_pts()), fill=255)
    out = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
    out.paste(layer, (0, 0), mask)
    od = ImageDraw.Draw(out)
    edge = c2 if pat == "solid" else (255, 255, 255)
    od.line(sc(_shield_pts() + [(3, 3)]), fill=edge + (200,), width=int(1.6 * S), joint="curve")
    od.text((20 * S, 27 * S), sig, fill=tc, font=get_font(int((12 if len(sig) > 2 else 14) * S), bold=True), anchor="mm")
    return out.resize((w, round(w * 1.15)), Image.LANCZOS)


# ----------------------------------------------------------------------------
# Card immagine
# ----------------------------------------------------------------------------
def _prob_color(p):
    return (16, 185, 129) if p >= 75 else (245, 158, 11) if p >= 60 else (239, 68, 68)


def _logo_ball(img, x, y, size, accent):
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([x, y, x + size, y + size], fill=(255, 255, 255), outline=accent, width=max(3, size // 14))
    cx, cy, r = x + size / 2, y + size / 2, size * .22
    pent = [(cx + r * math.sin(math.radians(a)), cy - r * math.cos(math.radians(a))) for a in range(0, 360, 72)]
    d.polygon(pent, fill=accent)
    for (px, py) in pent:
        dx, dy = px - cx, py - cy
        k = 1.9
        d.line([(px, py), (cx + dx * k, cy + dy * k)], fill=(11, 17, 32), width=max(2, size // 22))


def generate_card(title, subtitle, selection, avg_prob, vip_mode=False, out_path="card.png"):
    W, M = 1080, 44
    HEAD, RH, GAP, FOOT = 290, 164, 14, 260
    n = len(selection)
    H = HEAD + n * (RH + GAP) + FOOT

    if vip_mode:
        top, bot = (20, 15, 8), (8, 6, 4)
        card_bg, border = (30, 26, 20), (70, 55, 25)
        accent, accent2 = (245, 158, 11), (253, 224, 71)
    else:
        top, bot = (13, 22, 41), (8, 12, 24)
        card_bg, border = (22, 32, 54), (45, 58, 84)
        accent, accent2 = (16, 185, 129), (6, 182, 212)
    muted, white = (138, 151, 173), (240, 245, 252)

    img = Image.new("RGB", (W, H), top)
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / max(1, H - 1)
        px.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 520, -320, W + 220, 380], fill=accent + (70,))
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")

    # --- intestazione ---
    _logo_ball(img, M, 48, 78, accent)
    f_brand = get_font(56, heading=True)
    d.text((M + 100, 87), "352", fill=accent2, font=f_brand, anchor="lm")
    w352 = d.textlength("352 ", font=f_brand)
    d.text((M + 100 + w352, 87), "Pronostici", fill=white, font=f_brand, anchor="lm")
    tag = "VIP GOLD" if vip_mode else "ANALISI"
    f_tag = get_font(22, bold=True, heading=True)
    tw = d.textlength(tag, font=f_tag)
    d.rounded_rectangle([W - M - tw - 40, 62, W - M, 112], radius=25, fill=accent + (35,), outline=accent + (200,), width=2)
    d.text((W - M - tw / 2 - 20, 87), tag, fill=accent2, font=f_tag, anchor="mm")
    t_txt, t_font = fit_text(d, title, 38, W - 2 * M, heading=True, min_size=24)
    d.text((M, 168), t_txt, fill=white, font=t_font, anchor="lm")
    s_txt, s_font = fit_text(d, subtitle, 26, W - 2 * M, min_size=18)
    d.text((M, 214), s_txt, fill=muted, font=s_font, anchor="lm")
    d.rounded_rectangle([M, 252, W - M, 256], radius=2, fill=accent + (150,))

    # --- righe ---
    x_sh = M + 78
    x_name = x_sh + 38 + 16
    bx1 = W - M - 22
    bx0 = bx1 - 230
    max_name = bx0 - 26 - x_name
    for i, it in enumerate(selection, 1):
        y0 = HEAD + (i - 1) * (RH + GAP)
        locked = vip_mode and i > 3
        pc = _prob_color(it["prob"])
        d.rounded_rectangle([M, y0, W - M, y0 + RH], radius=28, fill=card_bg, outline=border, width=2)
        d.rounded_rectangle([M, y0 + 20, M + 9, y0 + RH - 20], radius=4, fill=(accent if locked else pc))
        d.text((M + 45, y0 + RH // 2), str(i), fill=muted, font=get_font(34, heading=True), anchor="mm")
        for k, (nm, st) in enumerate(((it["casa"], it.get("stemma_casa")), (it["trasf"], it.get("stemma_trasf")))):
            cy = y0 + 42 + k * 50
            sh = shield(nm, st, 38)
            img.paste(sh, (x_sh, cy - sh.height // 2), sh)
            txt, f = fit_text(d, nm, 31, max_name, bold=True, min_size=20)
            d.text((x_name, cy), txt, fill=white, font=f, anchor="lm")
        meta = " · ".join(x for x in (it["when"], it["compNome"]) if x)
        m_txt, m_font = fit_text(d, meta, 22, max_name, min_size=16)
        d.text((x_name, y0 + 130), m_txt, fill=muted, font=m_font, anchor="lm")
        bar_x1 = bx0 - 26
        if not locked:
            d.rounded_rectangle([x_name, y0 + RH - 18, bar_x1, y0 + RH - 12], radius=3, fill=(255, 255, 255, 25))
            d.rounded_rectangle([x_name, y0 + RH - 18, x_name + (bar_x1 - x_name) * it["prob"] / 100, y0 + RH - 12], radius=3, fill=pc)
        cx = (bx0 + bx1) // 2
        if locked:
            d.rounded_rectangle([bx0, y0 + 24, bx1, y0 + RH - 24], radius=22, fill=accent + (40,), outline=accent + (170,), width=2)
            ly = y0 + 46
            d.arc([cx - 11, ly, cx + 11, ly + 26], 180, 360, fill=accent2, width=5)
            d.rounded_rectangle([cx - 16, ly + 14, cx + 16, ly + 40], radius=6, fill=accent2)
            d.text((cx, y0 + 106), "AREA VIP", fill=accent2, font=get_font(22, bold=True, heading=True), anchor="mm")
        else:
            d.rounded_rectangle([bx0, y0 + 24, bx1, y0 + RH - 24], radius=22, fill=pc + (36,), outline=pc + (160,), width=2)
            l_txt, l_font = fit_text(d, it["label"], 22, bx1 - bx0 - 24, bold=True, heading=True, min_size=15)
            d.text((cx, y0 + 58), l_txt, fill=white, font=l_font, anchor="mm")
            d.text((cx, y0 + 102), f"{it['prob']}%", fill=pc, font=get_font(44, heading=True), anchor="mm")

    # --- piede ---
    yf = HEAD + n * (RH + GAP) + 4
    d.rounded_rectangle([M, yf, W - M, yf + 150], radius=28, fill=card_bg, outline=border, width=2)
    pcc = _prob_color(avg_prob)
    d.text((M + 36, yf + 42), "AFFIDABILITÀ MEDIA", fill=muted, font=get_font(22, bold=True), anchor="lm")
    d.text((M + 36, yf + 100), f"{avg_prob}%", fill=pcc, font=get_font(62, heading=True), anchor="lm")
    bx = M + 290
    d.rounded_rectangle([bx, yf + 62, W - M - 40, yf + 76], radius=7, fill=(255, 255, 255, 30))
    d.rounded_rectangle([bx, yf + 62, bx + (W - M - 40 - bx) * avg_prob / 100, yf + 76], radius=7, fill=pcc)
    d.text((bx, yf + 112), "Analisi complete nell'app 352 Pronostici", fill=muted, font=get_font(22), anchor="lm")
    d.text((W // 2, yf + 190), "18+  ·  Contenuti solo informativi e statistici  ·  Nessun invito al gioco", fill=muted, font=get_font(20), anchor="mm")
    d.text((W // 2, yf + 222), "Vietato ai minori di 18 anni", fill=muted, font=get_font(20), anchor="mm")

    img.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


# ----------------------------------------------------------------------------
# Telegram API (solo libreria standard)
# ----------------------------------------------------------------------------
def tg_call(method, fields, file_field=None):
    if not BOT_TOKEN or not CHAT_ID:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID mancanti: nessun invio.")
        return None
    boundary = "----352" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
    if file_field:
        name, path, ctype = file_field
        with open(path, "rb") as f:
            data = f.read()
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{os.path.basename(path)}"\r\n'
                      f'Content-Type: {ctype}\r\n\r\n').encode("utf-8") + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"{method}: ok={res.get('ok')}")
            return res
    except urllib.error.HTTPError as e:   # non stampiamo mai l'URL (contiene il token)
        print(f"{method}: errore HTTP {e.code}: {e.read()[:300]!r}")
    except Exception as e:
        print(f"{method}: errore {type(e).__name__}")
    return None


# ----------------------------------------------------------------------------
# Frasi variabili (tono da analista)
# ----------------------------------------------------------------------------
FORB = re.compile(r"\b(bet\w*|scommess\w*|quot[ae]|bookmaker\w*|puntat\w*|odds?|stake|euro|denaro|soldi|jackpot)\b|[€$£]", re.I)

OPEN_DAY = [
    "Si parte: ecco il quadro di oggi, {n} partite passate al setaccio.",
    "Il menu di oggi conta {n} eventi con numeri abbastanza leggibili.",
    "Giornata con {n} spunti interessanti, vediamoli in ordine.",
    "Lista pronta: {n} eventi, affidabilità media {avg}%.",
    "Primo giro di analisi: {n} gare con indicazioni chiare.",
    "Ecco cosa dicono i dati per oggi, {n} eventi in elenco.",
    "Si comincia con {n} partite che i modelli leggono bene.",
    "Quadro statistico del giorno: {n} eventi sopra la soglia di attenzione.",
    "Oggi {n} gare da tenere d'occhio, senza giri di parole.",
    "Aggiornamento della mattina: {n} eventi, tutti con dati alla mano.",
]
OPEN_AFTERNOON = [
    "Aggiornamento del pomeriggio: {n} eventi rivisti con i dati più freschi.",
    "Controllo di metà giornata, {n} partite in lista.",
    "Seconda lettura dei numeri: {n} eventi, qualcosa si è mosso.",
    "Ritocchi al quadro di oggi, restano {n} gare interessanti.",
    "Pomeriggio di calcio: {n} eventi con affidabilità media {avg}%.",
    "Ricalcolati i modelli sulle ultime info: {n} gare da guardare.",
    "Nuova selezione, {n} eventi con indicazioni abbastanza nette.",
    "Qui il punto dopo pranzo: {n} partite e numeri aggiornati.",
    "Rivista la lista, ora {n} eventi in evidenza.",
    "Dati aggiornati, {n} gare che meritano un'occhiata.",
]
OPEN_EVENING = [
    "Quadro serale: {n} eventi per chiudere la giornata.",
    "Ultimo giro di analisi, {n} partite in programma.",
    "Per stasera {n} gare con numeri interessanti.",
    "Multi-analisi della sera: {n} eventi, affidabilità media {avg}%.",
    "Serata di calcio, ecco {n} spunti statistici.",
    "Chiusura di giornata con {n} eventi sotto la lente.",
    "Stasera i numeri indicano {n} partite da seguire.",
    "Riepilogo dei match serali: {n} eventi in lista.",
    "Ultimo aggiornamento utile: {n} gare e dati rivisti.",
    "Si va verso sera, {n} eventi con indicazioni chiare.",
]
OPEN_VIP = [
    "Selezione riservata del Club: {n} analisi, le prime 3 in chiaro.",
    "Pacchetto VIP di oggi, {n} eventi con affidabilità media {avg}%.",
    "Top del giorno per il Club: {n} gare, tre visibili a tutti.",
    "Lista esclusiva pronta: {n} eventi, anteprima di tre.",
    "Selezione Gold: {n} partite, il resto è riservato.",
    "Anteprima VIP: tre eventi in chiaro su {n}.",
    "Le migliori letture del giorno, {n} in tutto.",
    "Edizione Gold di stasera: {n} analisi in elenco.",
    "Top {n} della giornata, qui l'anteprima.",
    "Il meglio dei modelli oggi: {n} eventi, tre sbloccati.",
]
OPENINGS = {"mattina": OPEN_DAY, "manuale": OPEN_DAY, "pomeriggio": OPEN_AFTERNOON,
            "sera": OPEN_EVENING, "vip": OPEN_VIP}

CTA = [
    "Formazioni probabili e tutti i mercati nell'app.",
    "Il dettaglio di ogni gara è nell'app, partita per partita.",
    "Nell'app trovi probabilità complete e marcatori.",
    "Analisi complete e mercati extra qui sotto, nell'app.",
    "Tutti i numeri per esteso nell'app.",
    "Per approfondire, scheda completa nell'app.",
    "Probabili formazioni, forma e mercati: li trovi nell'app.",
    "Il resto dei dati è nell'app, gara per gara.",
    "Apri l'app per vedere ogni analisi nel dettaglio.",
    "Sotto il pulsante per la scheda completa di ogni partita.",
]
CTA_VIP = [
    "Il Club è in attivazione: lista d'attesa aperta, sconto 20% ai primi iscritti.",
    "Iscrizione alla lista d'attesa VIP aperta, sconto del 20% per chi entra ora.",
    "Per il resto della selezione serve il Club: lista d'attesa con 20% di sconto.",
    "VIP in fase di lancio, i primi iscritti avranno il 20% di sconto.",
    "Le altre analisi sono riservate: lista d'attesa aperta, sconto 20%.",
    "Entra in lista d'attesa e ricevi l'avviso all'apertura, con 20% di sconto.",
    "Club in arrivo: iscriviti alla lista d'attesa, sconto 20% riservato.",
    "Il resto è nell'area VIP, attiva a breve: lista d'attesa con sconto 20%.",
    "Lista d'attesa VIP aperta, per i primi iscritti sconto del 20%.",
    "Serve il Pass per le restanti analisi: preiscrizione con 20% di sconto.",
]
CLOSINGS = [
    "Sono stime, non certezze.",
    "Il campo ha sempre l'ultima parola.",
    "Numeri alla mano, il resto lo fa il pallone.",
    "Probabilità, non garanzie.",
    "Ogni partita ha la sua storia: i dati ne leggono una parte.",
    "Occhio alle formazioni ufficiali prima del fischio.",
    "Le stime vanno lette come tendenze, non come promesse.",
    "Qualche variabile resta fuori dai modelli, come sempre.",
    "Buona lettura e buon calcio.",
    "Si vedrà a fine partita.",
]
NOTES_HEAD = [
    "Due righe sulle gare principali:",
    "Le note veloci:",
    "Cosa dicono i numeri, in breve:",
    "Il perché di ciascuna lettura:",
    "Motivazioni sintetiche:",
    "Qualche dettaglio sulle prime della lista:",
    "Appunti rapidi:",
    "Perché queste gare:",
    "Lettura dei dati, senza fronzoli:",
    "Il ragionamento in breve:",
]
NOTES = {
    "over": ["Media gol alta: ritmo da Over ({p}%).", "Squadre che segnano parecchio, Over a {p}%.",
             "Partita aperta sulla carta, Over {p}%.", "Reparti offensivi in palla, Over al {p}%."],
    "under": ["Gara da pochi gol, Under al {p}%.", "Difese solide, il modello dà Under {p}%.",
              "Ritmi bassi attesi, Under a {p}%.", "Pochi spazi previsti, Under {p}%."],
    "gol": ["Entrambe vanno a segno nel {p}% dei casi.", "Attacchi in forma, Goal a {p}%.",
            "Difese non impermeabili: Goal {p}%.", "Segnano in due, stima {p}%."],
    "nogol": ["Una delle due resta a secco, NoGoal {p}%.", "Attacco sterile da una parte, NoGoal al {p}%.",
              "Porta inviolata plausibile, NoGoal {p}%.", "Difesa ordinata, NoGoal a {p}%."],
    "casa": ["Il fattore campo pesa: vittoria casa al {p}%.", "In casa rende molto di più, 1 al {p}%.",
             "Squadra di casa favorita, stima {p}%.", "Peso del campo evidente, 1 a {p}%."],
    "trasf": ["Gli ospiti arrivano meglio: 2 al {p}%.", "Trasferta insidiosa per i padroni di casa, 2 {p}%.",
              "Qualità dalla parte degli ospiti, stima {p}%.", "Ospiti in vantaggio sui numeri, 2 al {p}%."],
    "eq": ["Equilibrio marcato, il pari vale {p}%.", "Gara bloccata sulla carta, X al {p}%.",
           "Poche differenze tra le due, pareggio {p}%.", "Match da doppia chance, X a {p}%."],
}
NOTE_KEY = {"over": "O2.5", "under": "U2.5", "gol": "GG", "nogol": "NG", "casa": "1", "trasf": "2", "eq": "X"}

RECAP_OPEN = [
    "Verifiche di {d}: ecco cosa è andato a segno.",
    "Controllo degli esiti di {d}, partiamo dai centrati.",
    "Chiudiamo il conto di {d}: queste le gare prese.",
    "Esiti di {d} alla mano, i pronostici centrati.",
    "Si guarda indietro a {d}: ecco i riscontri positivi.",
    "Giro di verifica su {d}, le prese:",
    "Com'è andata {d}: partiamo da quelle azzeccate.",
    "Riscontri di {d}, solo numeri.",
    "Check finale per {d}: queste le letture confermate.",
    "Confronto tra stime e risultati di {d}:",
]
RECAP_CLOSE = [
    "Il bilancio completo resta nell'app.",
    "Il dato conta sul lungo periodo, non sulla singola giornata.",
    "Avanti con la prossima giornata.",
    "Si riparte dai numeri di domani.",
    "Una giornata non fa una statistica.",
    "Tendenze, non certezze.",
    "Quello che conta è il campione ampio.",
    "Si aggiorna il registro e si va avanti.",
    "Le mancate restano nel conteggio, per trasparenza.",
    "A domani con nuove analisi.",
]
POLL_Q = [
    "Come finisce {a} - {b}?", "Il vostro 1X2 su {a} - {b}?", "{a} - {b}: che risultato vedete?",
    "Pronostico secco per {a} - {b}?", "Su {a} - {b} cosa succede?", "{a} - {b}, esito finale?",
    "Voi cosa dite di {a} - {b}?", "Esito di {a} - {b}: dite la vostra.", "{a} - {b}: 1, X o 2?",
    "Sondaggio lampo: {a} - {b}.",
]

_last_pick = {}
_sent_count = 0


def pick(key, options):
    """random.choice evitando di ripetere la stessa variante due volte di fila."""
    choices = [o for o in options if o != _last_pick.get(key)] or list(options)
    val = random.choice(choices)
    _last_pick[key] = val
    return val


def clean_txt(s):
    s = str(s or "")
    if not FORB.search(s):
        return s
    parts = re.findall(r"[^.!?]+[.!?]*", s)
    return " ".join(p.strip() for p in parts if not FORB.search(p))


def analyst_note(m):
    """Motivazione breve basata sui valori reali del file dati."""
    k = {**(m.get("prob_1x2") or {}), **(m.get("mercati_completi") or {})}

    def g(x):
        try:
            return float(k.get(x) or 0)
        except Exception:
            return 0.0
    cands = []
    if g("O2.5") >= 60: cands.append("over")
    if g("U2.5") >= 60: cands.append("under")
    if g("GG") >= 60: cands.append("gol")
    if g("NG") >= 60: cands.append("nogol")
    if g("1") >= 52: cands.append("casa")
    if g("2") >= 45: cands.append("trasf")
    if g("X") >= 30: cands.append("eq")
    if cands:
        key = random.choice(cands)
        return random.choice(NOTES[key]).format(p=int(round(g(NOTE_KEY[key]))))
    return clean_txt((m.get("pronostico_principale") or {}).get("motivazione_breve"))


# ----------------------------------------------------------------------------
# Invio messaggi (pulsanti, "typing...", pause)
# ----------------------------------------------------------------------------
def buttons(vip_mode=False):
    vip_txt = "💎 Lista d'attesa VIP · sconto 20%" if vip_mode else "💎 Entra nel VIP Club"
    return json.dumps({"inline_keyboard": [
        [{"text": "📲 Apri l'app · analisi complete", "url": app_link()}],
        [{"text": vip_txt, "url": app_link("vip")}],
    ]})


def send_chat_action(action="typing"):
    tg_call("sendChatAction", {"chat_id": CHAT_ID, "action": action})


def human_wait(action="typing", lo=1.5, hi=4.0):
    """Pausa 3-9 s tra messaggi consecutivi, poi 'typing...' e una breve attesa prima dell'invio."""
    global _sent_count
    if not BOT_TOKEN or not CHAT_ID:
        return
    if _sent_count > 0:
        time.sleep(random.uniform(3, 9))
    send_chat_action(action)
    time.sleep(random.uniform(lo, hi))
    _sent_count += 1


def send_photo(path, caption, vip_mode=False, silent=False):
    human_wait("upload_photo")
    res = tg_call("sendPhoto", {
        "chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML",
        "reply_markup": buttons(vip_mode), "disable_notification": "true" if silent else "false",
    }, ("photo", path, "image/png"))
    return bool(res and res.get("ok"))


def send_message(text, vip_mode=False, silent=True, with_buttons=True):
    human_wait("typing", 2.0, 5.0)
    fields = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true",
              "disable_notification": "true" if silent else "false"}
    if with_buttons:
        fields["reply_markup"] = buttons(vip_mode)
    res = tg_call("sendMessage", fields)
    return bool(res and res.get("ok"))


def send_poll(question, options, silent=True):
    human_wait("typing", 1.5, 3.0)
    res = tg_call("sendPoll", {
        "chat_id": CHAT_ID, "question": question[:300], "is_anonymous": "true",
        "options": json.dumps([{"text": o[:100]} for o in options]),
        "disable_notification": "true" if silent else "false",
    })
    return bool(res and res.get("ok"))


# ----------------------------------------------------------------------------
# Selezione e verifica esiti
# ----------------------------------------------------------------------------
def get_varied_trend(match, index):
    p1x2 = match.get("prob_1x2") or {}
    mc = match.get("mercati_completi") or {}
    groups = [
        ["1", "2", "1X+O1.5", "X2+O1.5"],
        ["O1.5", "O2.5", "GG", "MG2-4"],
        ["1X", "X2", "MG1-3", "U3.5"],
        ["1", "2", "GG", "O1.5"],
    ]
    preferred = groups[index % len(groups)]
    best_k, best_v = None, 0
    for k in preferred:
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


FIN_ST = {"FINISHED", "FT", "AET", "PEN"}
FIN_AFTER_MIN = 150


def final_score(m):
    """Punteggio finale: preferisce gol_casa/gol_trasf, poi ripiega su score."""
    try:
        if m.get("gol_casa") is not None and m.get("gol_trasf") is not None:
            return int(m["gol_casa"]), int(m["gol_trasf"])
    except Exception:
        pass
    sc = m.get("score")
    try:
        if isinstance(sc, (list, tuple)) and sc[0] is not None and sc[1] is not None:
            return int(sc[0]), int(sc[1])
    except Exception:
        pass
    return None


def is_concluso(m):
    """Conclusa: stato finale, oppure punteggio presente e inizio da oltre 150 minuti."""
    if not final_score(m):
        return False
    if str(m.get("stato") or "").upper() in FIN_ST:
        return True
    dt = parse_dt(m.get("data"))
    return bool(dt and (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)) > timedelta(minutes=FIN_AFTER_MIN))


def norm_esito(s):
    s = re.sub(r"\s+", "", str(s or "").upper().replace(",", "."))
    s = re.sub(r"^ESITO", "", s)
    s = s.replace("MULTIGOL", "MG").replace("NOGOAL", "NG").replace("NOGOL", "NG")
    s = s.replace("GOAL", "GG").replace("GOL", "GG").replace("OVER", "O").replace("UNDER", "U")
    return s


def _term(t, h, a):
    g = h + a
    if t == "1": return h > a
    if t == "X": return h == a
    if t == "2": return a > h
    if t == "1X": return h >= a
    if t == "X2": return a >= h
    if t == "12": return h != a
    if t == "GG": return h > 0 and a > 0
    if t == "NG": return not (h > 0 and a > 0)
    if t == "DNB1": return None if h == a else h > a
    if t == "DNB2": return None if h == a else a > h
    if t == "WIN0CASA": return h > a and a == 0
    if t == "WIN0TRASF": return a > h and h == 0
    if t == "CLEANSHEET1": return a == 0
    if t == "CLEANSHEET2": return h == 0
    r = re.fullmatch(r"([UO])(\d+)\.5", t)
    if r:
        return g < int(r[2]) + .5 if r[1] == "U" else g > int(r[2]) + .5
    r = re.fullmatch(r"MG(\d+)-(\d+)", t)
    if r:
        return int(r[1]) <= g <= int(r[2])
    return None


def eval_esito(esito, score):
    """True = centrato, False = mancato, None = non valutabile (o rimborso DNB)."""
    try:
        h, a = int(score[0]), int(score[1])
    except Exception:
        return None
    rs = [_term(t, h, a) for t in norm_esito(esito).split("+") if t]
    return None if (not rs or None in rs) else all(rs)


def build_recaps(matches, reported):
    """Un riepilogo per giorno con i pronostici centrati non ancora rendicontati.
    Ritorna [(giorno_iso, testo_o_None, [id_da_segnare])]."""
    by_day = {}
    for m in matches:
        pp = m.get("pronostico_principale") or {}
        dt = parse_dt(m.get("data"))
        if not pp or not dt or not is_concluso(m):
            continue
        sc = final_score(m)
        r = eval_esito(pp.get("esito"), sc)
        if r is None:
            continue
        by_day.setdefault(dt.date(), []).append((m, pp, sc, r))

    out = []
    for day in sorted(by_day):
        rows = by_day[day]
        fresh = [x for x in rows if str(x[0].get("id")) not in reported]
        if not fresh:
            continue
        ids = [str(x[0].get("id")) for x in fresh]
        hits = [x for x in fresh if x[3]]
        if not hits:
            out.append((day.isoformat(), None, ids))   # solo mancate: le segno senza inviare
            continue
        ok = sum(1 for x in rows if x[3])
        pct = round(ok * 100 / len(rows))
        hits.sort(key=lambda x: str(x[0].get("data")))
        dlabel = f"{GIORNI[day.weekday()]} {day.day} {MESI[day.month - 1]}"
        lines = [f"📊 <b>{html.escape(pick('ro', RECAP_OPEN).format(d=dlabel))}</b>", ""]
        for m, pp, sc, _ in hits[:25]:
            lines.append(f"✅ <b>PRESO</b> · {html.escape(clean_team(m.get('casa')))} - {html.escape(clean_team(m.get('trasf')))} "
                         f"<b>{sc[0]}-{sc[1]}</b> · {html.escape(str(pp.get('esito')))} "
                         f"({int(round(float(pp.get('probabilita') or 0)))}%)")
        lines += ["", f"🎯 Giornata: <b>{ok}/{len(rows)}</b> ({pct}%)", "",
                  f"<i>{html.escape(pick('rc', RECAP_CLOSE))} 18+ · Solo informativo e statistico.</i>"]
        out.append((day.isoformat(), "\n".join(lines), ids))
    return out


# ----------------------------------------------------------------------------
# Stato anti-doppioni
# ----------------------------------------------------------------------------
def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print("Stato non salvato:", type(e).__name__)


# ----------------------------------------------------------------------------
# Testi dei post
# ----------------------------------------------------------------------------
def build_caption(kind, slot, n, avg, vip_mode, oggi):
    opening = pick("op_" + slot, OPENINGS.get(slot, OPEN_DAY)).format(n=n, avg=avg)
    t = html.escape(kind.title())
    head = f"👑 <b>352 VIP Gold · {t}</b>" if vip_mode else f"⚽️ <b>352 Pronostici · {t}</b>"
    cta = pick("cta_vip", CTA_VIP) if vip_mode else pick("cta", CTA)
    return (f"{head}\n\n{html.escape(opening)}\n"
            f"📅 {oggi} · affidabilità media <b>{avg}%</b>\n\n"
            f"{html.escape(cta)}\n\n"
            f"<i>{html.escape(pick('cl', CLOSINGS))} 18+ · Solo informativo e statistico.</i>")


def build_notes(selection, vip_mode):
    visible = selection[:3] if vip_mode else selection[:4]
    lines = [f"<b>{html.escape(pick('nh', NOTES_HEAD))}</b>", ""]
    for x in visible:
        lines.append(f"▪️ {html.escape(x['casa'])} - {html.escape(x['trasf'])} · <b>{html.escape(x['label'])}</b> {x['prob']}%")
        if x.get("note"):
            lines.append(f"    {html.escape(x['note'])}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    if not os.path.exists(MATCHES_PATH):
        print("matches.json non trovato")
        return
    with open(MATCHES_PATH, "r", encoding="utf-8") as f:
        all_matches = json.load(f).get("matches", [])

    event = os.environ.get("GITHUB_EVENT_NAME", "")
    scheduled = event == "schedule"
    force = os.environ.get("FORCE_POST") == "1"
    hour = datetime.now(timezone.utc).hour
    today = datetime.now(ROME).date()
    today_s = today.isoformat()
    oggi = f"{today.day} {MESI[today.month - 1]} {today.year}"
    state = load_state()
    posted = state.setdefault("posted", {})

    def should(slot):          # un solo invio per fascia al giorno (solo sui run programmati)
        return (not scheduled) or force or posted.get(slot) != today_s

    def done(slot):
        posted[slot] = today_s

    # --- fascia oraria (UTC, come i cron del workflow) ---
    if scheduled and hour in (6, 7, 8):
        slot, kind, vip_mode, limit, silent = "mattina", "SELEZIONE MATTUTINA", False, 7, False
    elif scheduled and hour in (13, 14, 15):
        slot, kind, vip_mode, limit, silent = "pomeriggio", "ANALISI POMERIDIANA", False, 8, True
    elif scheduled and hour in (17, 18, 19):
        slot, kind, vip_mode, limit, silent = "sera", "MULTI-ANALISI SERALE", False, 12, True
    elif scheduled and hour in (21, 22, 23):
        slot, kind, vip_mode, limit, silent = "vip", "SELEZIONE ESCLUSIVA · TOP VIP", True, 6, False
    else:
        slot, kind, vip_mode, limit, silent = "manuale", "SELEZIONE DEL GIORNO", False, 8, False

    # --- riepilogo dei pronostici centrati non ancora rendicontati ---
    reported = state.setdefault("reported", {})
    for day_s, text, ids in build_recaps(all_matches, reported):
        if text is None or send_message(text, silent=True, with_buttons=False):
            for i in ids:
                reported[i] = day_s
    lim = (today - timedelta(days=60)).isoformat()
    for i in [k for k, v in reported.items() if v < lim]:
        del reported[i]

    # --- schedina grafica ---
    timed = [m for m in all_matches if m.get("stato") == "TIMED"]
    pool = timed if timed else all_matches
    enriched = []
    for idx, m in enumerate(pool):
        label, prob = get_varied_trend(m, idx)
        dt = parse_dt(m.get("data"))
        enriched.append({
            "casa": clean_team(m.get("casa", "")), "trasf": clean_team(m.get("trasf", "")),
            "stemma_casa": m.get("stemma_casa"), "stemma_trasf": m.get("stemma_trasf"),
            "compNome": m.get("compNome", "Calcio"), "dt": dt, "when": fmt_when(dt),
            "label": label, "prob": prob, "aff": m.get("affidabilita") or 0,
            "note": analyst_note(m),
        })
    enriched.sort(key=lambda x: (-x["prob"], x["dt"] or datetime.max.replace(tzinfo=timezone.utc)))
    selection = enriched[:limit]

    if selection and should(slot):
        n = len(selection)
        avg = round(sum(x["prob"] for x in selection) / n)
        title = f"{kind}  •  {n} EVENTI"
        subtitle = f"Elaborazione algoritmo 352 • {oggi}"
        card = generate_card(title, subtitle, selection, avg, vip_mode=vip_mode)
        caption = build_caption(kind, slot, n, avg, vip_mode, oggi)
        if send_photo(card, caption, vip_mode=vip_mode, silent=silent):
            done(slot)
            # note sintetiche (breve messaggio separato, senza muri di testo)
            send_message(build_notes(selection, vip_mode), vip_mode=vip_mode, silent=True, with_buttons=False)
            # sondaggio 1-X-2 sulla gara di oggi con affidabilita' piu' alta (solo mattina)
            if slot == "mattina" and should("sondaggio"):
                cand = [x for x in enriched if x["dt"] and x["dt"].date() == today]
                if cand:
                    g = max(cand, key=lambda x: x["aff"])
                    q = pick("pq", POLL_Q).format(a=g["casa"], b=g["trasf"])
                    if send_poll(q, [f"1 · {g['casa']}", "X · Pareggio", f"2 · {g['trasf']}"]):
                        done("sondaggio")
    elif selection:
        print(f"Fascia '{slot}' gia' pubblicata oggi: nessun doppione.")
    else:
        print("Nessuna partita da pubblicare.")

    save_state(state)


if __name__ == "__main__":
    main()
