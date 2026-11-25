#!/usr/bin/env python3
"""352 Pronostici - generatore video TikTok giornaliero.

Legge public/matches.json (oppure public/data/matches.json) e produce:
  - output/tiktok_daily.mp4      (1080x1920, 30 fps, 14 s, H.264 + AAC)
  - output/tiktok_caption.txt    (descrizione breve + 6 hashtag)

Requisiti: Pillow, numpy, ffmpeg nel PATH (gia' presente su ubuntu-latest di GitHub Actions).
Font facoltativi in scripts/fonts/ (Outfit-Bold.ttf, PlusJakartaSans-Bold.ttf, PlusJakartaSans-Regular.ttf);
senza di essi si usa DejaVu / Liberation.

Uso:  python tiktok_generator.py
"""
import os
import re
import sys
import json
import wave
import random
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from zoneinfo import ZoneInfo
    ROME = ZoneInfo("Europe/Rome")
except Exception:  # fallback prudente se manca tzdata
    ROME = timezone(timedelta(hours=1))

# ----------------------------------------------------------------------------
# Costanti
# ----------------------------------------------------------------------------
W, H = 1080, 1920
FPS = 30
DUR = 14
FRAMES = FPS * DUR
OUT_DIR = "output"
OUT_VIDEO = os.path.join(OUT_DIR, "tiktok_daily.mp4")
OUT_CAPTION = os.path.join(OUT_DIR, "tiktok_caption.txt")
OUT_AUDIO = os.path.join(OUT_DIR, "_audio_tmp.wav")
OUT_LOG = os.path.join(OUT_DIR, "ffmpeg.log")

BG = (11, 17, 32)          # #0B1120
CARD = (19, 28, 49)        # #131C31
BORDER = (40, 54, 82)
EMER = (16, 185, 129)      # #10B981
GOLD = (245, 158, 11)      # #F59E0B
CYAN = (6, 182, 212)
RED = (239, 68, 68)
WHITE = (240, 245, 252)
MUTED = (138, 151, 173)
TRACK = (38, 50, 76)

MARGIN = 60
CARD_W, CARD_H, CARD_GAP = W - 2 * MARGIN, 356, 26
CARDS_Y = 460
CARD_START = [1.3, 3.1, 4.9]     # secondi in cui entra ogni card
SLIDE = 0.6
BAR_DUR = 1.3
RECAP_T = 9.0
FOOTER_T = 10.0

GIORNI_FULL = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI_FULL = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
             "settembre", "ottobre", "novembre", "dicembre"]
GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

LABELS = {
    "1": "1 FISSO", "X": "PAREGGIO X", "2": "2 FISSO",
    "1X": "1X", "X2": "X2", "12": "12",
    "GG": "GOAL (GG)", "NG": "NOGOAL",
    "O1.5": "OVER 1.5", "U2.5": "UNDER 2.5", "O2.5": "OVER 2.5",
    "U3.5": "UNDER 3.5", "MG1-3": "MULTIGOL 1-3", "MG2-4": "MULTIGOL 2-4",
    "1X+O1.5": "1X + OVER 1.5", "X2+O1.5": "X2 + OVER 1.5",
}
BEST_KEYS = list(LABELS.keys())

HOOKS = [
    "Tre partite, numeri chiari: ecco il radar del giorno.",
    "Cosa dicono i dati sulle gare in programma?",
    "Il radar AI ha fatto i conti: ecco le prime tre letture.",
    "Tre gare da tenere d'occhio, senza giri di parole.",
    "I numeri parlano chiaro su queste tre partite.",
    "Le tre letture statistiche più solide della giornata.",
    "Prima del fischio d'inizio, guarda cosa dicono i dati.",
    "Tre partite, zero chiacchiere: solo probabilità.",
]
CAPTION_OPEN = [
    "Radar AI di giornata: tre letture che i numeri sostengono bene.",
    "Tre partite, un filo comune: le probabilità sono nette.",
    "Forma, fattore campo e media gol: ecco cosa emerge oggi dai dati.",
    "Il quadro statistico del giorno, senza fronzoli.",
    "Tre gare in cui i modelli vedono un margine chiaro.",
    "Un'occhiata veloce ai numeri prima del fischio d'inizio.",
    "Le selezioni statistiche di oggi, in meno di un minuto.",
    "Cosa dice il radar sulle partite del giorno.",
]
CAPTION_CLOSE = [
    "Sono stime, non certezze: il campo ha sempre l'ultima parola.",
    "Probabilità, non garanzie.",
    "Le stime vanno lette come tendenze, non come promesse.",
    "Occhio alle formazioni ufficiali prima del fischio.",
    "Qualche variabile resta fuori dai modelli, come sempre.",
    "Numeri alla mano, il resto lo fa il pallone.",
]
HASHTAGS = ["#calcio", "#seriea", "#statistichecalcio", "#pronostici", "#analisitattica", "#352pronostici"]

# Compliance editoriale: nessun riferimento a denaro o gioco nei testi generati
FORB = re.compile(r"\b(bet\w*|scommess\w*|quot[ae]|bookmaker\w*|puntat\w*|odds?|stake|euro|denaro|soldi|jackpot)\b|[€$£]", re.I)


def clean_txt(s):
    s = str(s or "")
    if not FORB.search(s):
        return s
    parts = re.findall(r"[^.!?]+[.!?]*", s)
    return " ".join(p.strip() for p in parts if not FORB.search(p))


# ----------------------------------------------------------------------------
# Font
# ----------------------------------------------------------------------------
_BASE = os.path.dirname(os.path.abspath(__file__))
_FONT_DIRS = [os.path.join(_BASE, "fonts"), os.path.join(_BASE, "scripts", "fonts"),
              os.path.join(os.getcwd(), "scripts", "fonts"), os.path.join(os.getcwd(), "fonts")]
_DJ = "/usr/share/fonts/truetype/dejavu/"
_LB = "/usr/share/fonts/truetype/liberation/"


@lru_cache(maxsize=None)
def get_font(size, bold=False, heading=False):
    names = ["Outfit-Bold.ttf", "PlusJakartaSans-Bold.ttf"] if heading else \
            ["PlusJakartaSans-Bold.ttf"] if bold else ["PlusJakartaSans-Regular.ttf"]
    cands = [os.path.join(d, n) for d in _FONT_DIRS for n in names]
    heavy = bold or heading
    cands += [_DJ + ("DejaVuSans-Bold.ttf" if heavy else "DejaVuSans.ttf"),
              _LB + ("LiberationSans-Bold.ttf" if heavy else "LiberationSans-Regular.ttf")]
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def fit_text(draw, text, size, max_w, bold=False, heading=False, min_size=16):
    """Riduce il corpo finche' il testo entra in max_w; se serve tronca con '…'."""
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


def wrap_lines(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------------
# Utilità dati
# ----------------------------------------------------------------------------
_STRIP = re.compile(
    r"\b(?:FC|CF|AFC|AC|ACF|AS|SS|SSC|US|SV|SK|KV|FK|SE|BC|CD|UD|RC|RCD|SC|Club|Calcio|ŠK)\b", re.IGNORECASE)
_NUMS = re.compile(r"\b\d{2,4}\b")
ABBR = {
    "internazionale milano": "Inter", "internazionale": "Inter", "hellas verona": "Verona",
    "manchester city": "Man City", "manchester united": "Man United",
    "tottenham hotspur": "Tottenham", "newcastle united": "Newcastle",
    "wolverhampton wanderers": "Wolves", "brighton & hove albion": "Brighton",
    "west ham united": "West Ham", "nottingham forest": "Nottm Forest",
    "atlético de madrid": "Atlético", "borussia dortmund": "Dortmund", "bayer leverkusen": "Leverkusen",
    "bayern münchen": "Bayern", "paris saint-germain": "PSG", "olympique de marseille": "Marsiglia",
    "olympique lyonnais": "Lione", "sporting clube de portugal": "Sporting CP", "sl benfica": "Benfica",
}


def clean_team(name):
    n = _STRIP.sub(" ", str(name or ""))
    n = _NUMS.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip(" -.")
    return ABBR.get(n.casefold(), n) or str(name or "")


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


def to_f(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def prob_color(p):
    return EMER if p >= 75 else GOLD if p >= 60 else RED


def load_matches():
    roots = [os.getcwd(), _BASE, os.path.dirname(_BASE)]
    rels = [os.path.join("public", "matches.json"), os.path.join("public", "data", "matches.json")]
    for root in roots:
        for rel in rels:
            p = os.path.join(root, rel)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    j = json.load(f)
                print("Dati letti da:", p)
                return j if isinstance(j, list) else (j.get("matches") or [])
    raise FileNotFoundError("matches.json non trovato in public/ o public/data/")


# ----------------------------------------------------------------------------
# Verifica esiti (stessa logica dell'app)
# ----------------------------------------------------------------------------
FIN_ST = {"FINISHED", "FT", "AET", "PEN"}
LIVE_ST = {"IN_PLAY", "PAUSED", "LIVE", "1H", "2H", "HT", "ET"}
FIN_AFTER_MIN = 150


def final_score(m):
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
    r = re.fullmatch(r"([UO])(\d+)\.5", t)
    if r:
        return g < int(r[2]) + .5 if r[1] == "U" else g > int(r[2]) + .5
    r = re.fullmatch(r"MG(\d+)-(\d+)", t)
    if r:
        return int(r[1]) <= g <= int(r[2])
    return None


def eval_esito(esito, score):
    """True = centrato, False = mancato, None = non valutabile."""
    try:
        h, a = int(score[0]), int(score[1])
    except Exception:
        return None
    rs = [_term(t, h, a) for t in norm_esito(esito).split("+") if t]
    return None if (not rs or None in rs) else all(rs)


def yesterday_recap(matches, today):
    """Ritorna (centrate, verificate) per le partite concluse di ieri."""
    y = today - timedelta(days=1)
    ok = tot = 0
    for m in matches:
        pp = m.get("pronostico_principale") or {}
        dt = parse_dt(m.get("data"))
        if not pp or not dt or dt.date() != y or not is_concluso(m):
            continue
        r = eval_esito(pp.get("esito"), final_score(m))
        if r is None:
            continue
        tot += 1
        ok += 1 if r else 0
    return ok, tot


# ----------------------------------------------------------------------------
# Selezione contenuti
# ----------------------------------------------------------------------------
def analyse(m, dt):
    vals = {}
    for src in (m.get("prob_1x2"), m.get("mercati_completi")):
        if isinstance(src, dict):
            for k, v in src.items():
                vals[str(k)] = to_f(v)
    best_k, best_v = None, 0.0
    for k in BEST_KEYS:
        if vals.get(k, 0) > best_v:
            best_k, best_v = k, vals[k]
    pp = m.get("pronostico_principale") or {}
    if pp.get("esito") and to_f(pp.get("probabilita")) > best_v:
        key = norm_esito(pp.get("esito"))
        best_k, best_v = key, to_f(pp.get("probabilita"))
    surp = None
    x2, p1, gg = vals.get("X2", 0), vals.get("1"), vals.get("GG", 0)
    if x2 >= 62 and p1 is not None and "1" in vals and p1 < 45:
        surp = ("X2", x2)
    if gg >= 72 and (surp is None or gg > surp[1]):
        surp = ("GG", gg)
    return {"m": m, "dt": dt, "best": (best_k, best_v), "surp": surp}


def make_item(c, key, val, tag):
    m = c["m"]
    aff = m.get("affidabilita")
    return {
        "casa": clean_team(m.get("casa")), "trasf": clean_team(m.get("trasf")),
        "comp": clean_txt(m.get("compNome") or "Calcio"), "when": fmt_when(c["dt"]),
        "label": LABELS.get(key, str(key).upper()), "prob": int(round(val)),
        "aff": None if aff is None else int(round(to_f(aff))), "tag": tag, "id": m.get("id"),
    }


def select_items(matches, now):
    today, tomorrow = now.date(), (now + timedelta(days=1)).date()
    pool = []
    for m in matches:
        st = str(m.get("stato") or "").upper()
        dt = parse_dt(m.get("data"))
        if not dt or st in FIN_ST or st in LIVE_ST or dt <= now:
            continue
        pool.append(analyse(m, dt))
    near = [c for c in pool if c["dt"].date() in (today, tomorrow)]
    pool = near if near else [c for c in pool if c["dt"] <= now + timedelta(days=3)]
    if not pool:
        return []

    chosen, used = [], set()

    def add(c, key, val, tag):
        if len(chosen) < 3 and id(c) not in used and key:
            used.add(id(c))
            chosen.append(make_item(c, key, val, tag))

    for c in sorted([c for c in pool if c["best"][1] >= 72], key=lambda c: (-c["best"][1], c["dt"])):
        add(c, c["best"][0], c["best"][1], "TOP")
    for c in sorted([c for c in pool if c["surp"]], key=lambda c: (-c["surp"][1], c["dt"])):
        add(c, c["surp"][0], c["surp"][1], "RADAR SORPRESA")
    for c in sorted(pool, key=lambda c: (-c["best"][1], c["dt"])):
        add(c, c["best"][0], c["best"][1], "ANALISI")
    return chosen


# ----------------------------------------------------------------------------
# Grafica
# ----------------------------------------------------------------------------
def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out(t):
    return 1 - (1 - clamp01(t)) ** 3


def fade(img, k):
    if k >= 1:
        return img
    a = img.getchannel("A").point(lambda v: int(v * k))
    out = img.copy()
    out.putalpha(a)
    return out


def build_background():
    top = np.array([15, 24, 44], np.float32)
    bot = np.array(BG, np.float32)
    ramp = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    grad = top + (bot - top) * ramp                      # (H, 3)
    arr = np.repeat(grad[:, None, :], W, axis=1).astype(np.uint8)
    img = Image.fromarray(arr, "RGB").convert("RGBA")
    glow = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W // 4 - 200, -140, W // 4 + 120, 190], fill=EMER + (95,))
    gd.ellipse([-120, H // 4 - 210, 170, H // 4 + 40], fill=GOLD + (55,))
    glow = glow.filter(ImageFilter.GaussianBlur(34)).resize((W, H), Image.BICUBIC)
    return Image.alpha_composite(img, glow).convert("RGB")


def date_it(d):
    return f"{GIORNI_FULL[d.weekday()]} {d.day} {MESI_FULL[d.month - 1]} {d.year}"


def render_header(date_txt, hook):
    img = Image.new("RGBA", (W, 440), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    txt, f = fit_text(d, "352 PRONOSTICI · RADAR AI", 46, W - 2 * MARGIN, heading=True, min_size=28)
    d.text((MARGIN, 112), txt, fill=EMER, font=f, anchor="lm")
    d.text((MARGIN, 172), date_txt, fill=MUTED, font=get_font(34), anchor="lm")
    d.rounded_rectangle([MARGIN, 214, MARGIN + 130, 220], radius=3, fill=GOLD)
    size = 62
    while True:
        font = get_font(size, bold=True)
        lines = wrap_lines(d, hook, font, W - 2 * MARGIN)
        if len(lines) <= 2 or size <= 36:
            break
        size -= 2
    for i, line in enumerate(lines[:2]):
        d.text((MARGIN, 262 + i * (size + 14)), line, fill=WHITE, font=font, anchor="lt")
    return img


def render_card(item, idx):
    w, h = CARD_W, CARD_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pc = prob_color(item["prob"])
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=40, fill=CARD + (255,), outline=BORDER + (255,), width=2)
    d.rounded_rectangle([0, 44, 10, h - 44], radius=5, fill=pc + (255,))
    # numero + competizione/orario
    d.ellipse([36, 36, 92, 92], fill=pc + (255,))
    d.text((64, 64), str(idx + 1), fill=BG, font=get_font(34, heading=True), anchor="mm")
    tag_col = EMER if item["tag"] == "TOP" else GOLD if item["tag"] == "RADAR SORPRESA" else CYAN
    tf = get_font(22, bold=True, heading=True)
    tw = d.textlength(item["tag"], font=tf)
    tx0 = w - 40 - tw - 36
    d.rounded_rectangle([tx0, 40, w - 40, 88], radius=24, fill=tag_col + (45,), outline=tag_col + (230,), width=2)
    d.text(((tx0 + w - 40) / 2, 64), item["tag"], fill=tag_col, font=tf, anchor="mm")
    meta = " · ".join(x for x in (item["when"], item["comp"]) if x)
    m_txt, m_font = fit_text(d, meta, 26, tx0 - 120 - 20, min_size=16)
    d.text((112, 64), m_txt, fill=MUTED, font=m_font, anchor="lm")
    # squadre
    for k, name in enumerate((item["casa"], item["trasf"])):
        t, f = fit_text(d, name, 44, w - 80, bold=True, min_size=24)
        d.text((40, 136 + k * 56), t, fill=WHITE, font=f, anchor="lm")
    # mercato consigliato
    m_txt, m_font = fit_text(d, "Consigliato · " + item["label"], 38, 560, bold=True, min_size=22)
    d.text((40, 250), m_txt, fill=GOLD, font=m_font, anchor="lm")
    # indice affidabilità
    if item["aff"] is not None:
        a = max(0, min(100, item["aff"]))
        lab = "Indice affidabilità "
        lf = get_font(24)
        d.text((40, 338), lab, fill=MUTED, font=lf, anchor="lm")
        d.text((40 + d.textlength(lab, font=lf), 338), f"{a}%", fill=prob_color(a), font=get_font(26, bold=True), anchor="lm")
    else:
        d.text((40, 338), "Stima statistica del modello", fill=MUTED, font=get_font(24), anchor="lm")
    return img


def render_recap(ok, tot):
    w, h = CARD_W, 80
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=40, fill=EMER + (50,), outline=EMER + (230,), width=3)
    d.text((w // 2, h // 2), f"IERI: {ok}/{tot} CENTRATE", fill=WHITE, font=get_font(40, heading=True), anchor="mm")
    return img


def render_footer():
    w, h = CARD_W, 120
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=40, fill=CARD + (255,))
    t, f = fit_text(d, "Analisi completa gratis sull'app · Solo 18+", 38, w - 60, bold=True, min_size=22)
    d.text((w // 2, 44), t, fill=WHITE, font=f, anchor="mm")
    d.text((w // 2, 88), "352 Pronostici · Contenuto informativo e statistico", fill=MUTED, font=get_font(24), anchor="mm")
    return img


# ----------------------------------------------------------------------------
# Audio sintetizzato (beat + pad ambient)
# ----------------------------------------------------------------------------
def synth_audio(path):
    sr = 44100
    n = int(sr * DUR)
    t_all = np.arange(n) / sr
    rng = np.random.default_rng(352)
    mix = np.zeros(n, np.float64)
    beat = 60.0 / 96

    kn = int(0.28 * sr)
    kt = np.arange(kn) / sr
    kick = np.sin(2 * np.pi * (48 * kt + (95 / 22) * (1 - np.exp(-22 * kt)))) * np.exp(-kt * 11)
    hn = int(0.07 * sr)
    ht = np.arange(hn) / sr
    k = 0
    while k * beat < DUR:
        s = int(k * beat * sr)
        e = min(n, s + kn)
        if s < n:
            mix[s:e] += 0.55 * kick[:e - s]
        s2 = int((k * beat + beat / 2) * sr)
        if s2 < n:
            noise = np.diff(rng.standard_normal(hn + 1))
            e2 = min(n, s2 + hn)
            mix[s2:e2] += 0.12 * (noise * np.exp(-ht * 55))[:e2 - s2]
        k += 1

    chords = [[220.00, 261.63, 329.63], [174.61, 220.00, 261.63],
              [261.63, 329.63, 392.00], [196.00, 246.94, 293.66]]
    roots = [55.00, 43.65, 65.41, 49.00]
    seg, ln = 3.5, int(4.2 * sr)
    env_full = np.hanning(ln)
    for i, (chord, root) in enumerate(zip(chords, roots)):
        s = int(i * seg * sr)
        e = min(n, s + ln)
        if s >= n:
            break
        tt = np.arange(e - s) / sr
        env = env_full[:e - s]
        pad = np.zeros(e - s)
        for fr in chord:
            pad += np.sin(2 * np.pi * fr * tt) + 0.5 * np.sin(2 * np.pi * fr * 1.004 * tt)
        pad *= 0.05 * (0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * tt))
        bass = 0.18 * np.sin(2 * np.pi * root * tt)
        mix[s:e] += (pad + bass) * env

    peak = float(np.max(np.abs(mix))) or 1.0
    mix = mix / peak * 0.32                              # volume basso
    mix *= np.minimum(1.0, t_all / 0.5) * np.minimum(1.0, (DUR - t_all) / 1.0)
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    stereo = np.column_stack((pcm, pcm))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


# ----------------------------------------------------------------------------
# Video
# ----------------------------------------------------------------------------
def render_video(items, date_txt, hook, recap):
    bg = build_background()
    header = render_header(date_txt, hook)
    cards = [render_card(it, i) for i, it in enumerate(items)]
    recap_img = render_recap(*recap) if recap else None
    footer = render_footer()

    synth_audio(OUT_AUDIO)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", OUT_AUDIO,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
           "-movflags", "+faststart", "-t", str(DUR), OUT_VIDEO]
    log = open(OUT_LOG, "w")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)

    fx, fy = MARGIN, 1730
    try:
        for f in range(FRAMES):
            t = f / FPS
            fr = bg.copy()
            d = ImageDraw.Draw(fr)

            # barra di avanzamento sottile in alto
            d.rectangle([0, 0, int(W * t / DUR), 8], fill=EMER)

            # header
            hl = fade(header, ease_out(t / 0.8))
            fr.paste(hl, (0, 0), hl)

            # card con ingresso dal basso, barra e numero progressivi
            for i, card in enumerate(cards):
                ts = CARD_START[i] if i < len(CARD_START) else CARD_START[-1] + 1.8 * (i - 2)
                if t < ts:
                    continue
                k = clamp01((t - ts) / SLIDE)
                e = ease_out(k)
                x = MARGIN
                y = CARDS_Y + i * (CARD_H + CARD_GAP) + int((1 - e) * 140)
                layer = card if k >= 1 else fade(card, e)
                fr.paste(layer, (x, y), layer)
                if k >= 1:
                    be = ease_out((t - ts - SLIDE) / BAR_DUR)
                    it = items[i]
                    pc = prob_color(it["prob"])
                    bx0, bx1 = x + 40, x + CARD_W - 40
                    d.rounded_rectangle([bx0, y + 296, bx1, y + 312], radius=8, fill=TRACK)
                    fw = (bx1 - bx0) * it["prob"] / 100.0 * be
                    if fw >= 1:
                        d.rounded_rectangle([bx0, y + 296, bx0 + max(fw, 2), y + 312], radius=8, fill=pc)
                    d.text((x + CARD_W - 40, y + 250), f"{int(it['prob'] * be)}%",
                           fill=pc, font=get_font(64, heading=True), anchor="rm")

            # badge riepilogo di ieri
            if recap_img is not None and t >= RECAP_T:
                rl = fade(recap_img, ease_out((t - RECAP_T) / 0.5))
                fr.paste(rl, (MARGIN, 1618), rl)

            # footer con call-to-action e bordo pulsante
            if t >= FOOTER_T:
                fl = fade(footer, ease_out((t - FOOTER_T) / 0.6))
                fr.paste(fl, (fx, fy), fl)
                pulse = 0.5 + 0.5 * np.sin(2 * np.pi * 0.9 * (t - FOOTER_T))
                col = tuple(int(EMER[j] + (GOLD[j] - EMER[j]) * pulse) for j in range(3))
                if t >= FOOTER_T + 0.6:
                    d.rounded_rectangle([fx, fy, fx + CARD_W - 1, fy + 119], radius=40, outline=col, width=4)

            proc.stdin.write(fr.tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    rc = proc.wait()
    log.close()
    if os.path.exists(OUT_AUDIO):
        os.remove(OUT_AUDIO)
    if rc != 0:
        tail = ""
        try:
            with open(OUT_LOG, "r") as lf:
                tail = lf.read()[-800:]
        except Exception:
            pass
        raise RuntimeError(f"ffmpeg terminato con codice {rc}. {tail}")


# ----------------------------------------------------------------------------
# Caption
# ----------------------------------------------------------------------------
def build_caption(items, recap):
    lines = [random.choice(CAPTION_OPEN), ""]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['casa']} - {it['trasf']} · {it['label']} {it['prob']}%")
    lines.append("")
    if recap:
        lines.append(f"Ieri: {recap[0]}/{recap[1]} pronostici principali centrati.")
    lines.append(random.choice(CAPTION_CLOSE))
    lines.append("Analisi complete gratis sull'app. 18+ · Solo informativo e statistico.")
    lines.append("")
    tags = HASHTAGS[:]
    random.shuffle(tags)
    lines.append(" ".join(tags))
    return clean_txt_keep_lines("\n".join(lines))


def clean_txt_keep_lines(text):
    return "\n".join(clean_txt(l) if not l.startswith("#") else l for l in text.split("\n"))


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    if shutil.which("ffmpeg") is None:
        print("ERRORE: ffmpeg non trovato nel PATH (su Ubuntu: sudo apt-get install -y ffmpeg).")
        sys.exit(1)
    os.makedirs(OUT_DIR, exist_ok=True)

    matches = load_matches()
    now = datetime.now(ROME)
    items = select_items(matches, now)
    if not items:
        print("Nessuna partita in programma da mostrare: video non generato.")
        sys.exit(0)

    recap = None
    ok, tot = yesterday_recap(matches, now.date())
    if tot > 0 and ok > 0:
        recap = (ok, tot)

    hook = random.choice(HOOKS)
    date_txt = date_it(now.date())
    print(f"Selezionate {len(items)} partite: " + ", ".join(f"{i['casa']}-{i['trasf']} ({i['tag']})" for i in items))
    if recap:
        print(f"Riepilogo ieri: {recap[0]}/{recap[1]}")

    render_video(items, date_txt, hook, recap)
    with open(OUT_CAPTION, "w", encoding="utf-8") as f:
        f.write(build_caption(items, recap) + "\n")
    print("Creati:", OUT_VIDEO, "e", OUT_CAPTION)


if __name__ == "__main__":
    main()
