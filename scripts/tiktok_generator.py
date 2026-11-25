import os, json, math, wave, random, subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 14.5
OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)
DATA_PATH = "public/data/matches.json" if os.path.exists("public/data/matches.json") else "public/matches.json"

HOOKS = [
    "3 SEGNALI FORTI\nDELL'ALGORITMO OGGI",
    "ATTENZIONE A QUESTE\n3 GARANZIE DI OGGI",
    "RADAR AI: I 3 ESITI\nPIÙ SOLIDI DEL GIORNO",
    "ECCO COSA HA TROVATO\nL'ALGORITMO OGGI"
]
CAPTIONS = [
    "L'algoritmo 352 ha analizzato tutte le gare di oggi e isolato i 3 segnali più solidi. Trovi tutti i 38 mercati gratis sull'app (link in bio).",
    "Analisi statistica completa delle migliori 3 partite del giorno. Scopri anche il Radar Sorprese gratuito sull'app 352 Pronostici (link in bio).",
    "Dati alla mano: ecco le 3 gare con l'indice di affidabilità più alto oggi. Tutte le probabilità aggiornate sull'app gratuita in bio."
]
MESI = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

def load_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

F_TAG, F_DATE, F_HOOK = load_font(28, True), load_font(26, False), load_font(54, True)
F_META, F_BADGE, F_TEAM = load_font(24, False), load_font(22, True), load_font(40, True)
F_PICK, F_PCT, F_SUB = load_font(30, True), load_font(54, True), load_font(23, False)
F_CTA_TITLE, F_CTA_SUB, F_CTA_BTN = load_font(62, True), load_font(32, False), load_font(36, True)

def get_matches():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    matches = raw if isinstance(raw, list) else raw.get("partite") or raw.get("matches") or []
    upcoming = [m for m in matches if m.get("stato") not in ("FINISHED", "FT") and m.get("pronostico_principale")]
    upcoming.sort(key=lambda m: float(m.get("pronostico_principale", {}).get("probabilita", 0)), reverse=True)
    return upcoming[:3] if len(upcoming) >= 3 else matches[:3]

def make_audio(path):
    sr, n_samples = 44100, int(44100 * DUR)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        buf = bytearray()
        for i in range(n_samples):
            t = i / sr
            beat = (t * 2.0) % 1.0
            kick = math.exp(-beat * 14.0) * math.sin(2 * math.pi * 58 * t) * 0.35
            pad = (math.sin(2 * math.pi * 110 * t) + 0.5 * math.sin(2 * math.pi * 165 * t)) * 0.08
            env = min(1.0, t / 0.5) * min(1.0, (DUR - t) / 0.6)
            val = int(max(-32767, min(32767, (kick + pad) * env * 22000)))
            buf.extend(val.to_bytes(2, "little", signed=True))
        wf.writeframes(buf)

def draw_base_bg():
    img = Image.new("RGB", (W, H), (11, 17, 32))
    d = ImageDraw.Draw(img, "RGBA")
    for r in range(520, 0, -20):
        alpha = int(28 * (1 - r / 520))
        d.ellipse((W - 220 - r, 120 - r, W - 220 + r, 120 + r), fill=(16, 185, 129, alpha))
        d.ellipse((140 - r, 1180 - r, 140 + r, 1180 + r), fill=(245, 158, 11, int(alpha * 0.65)))
    return img

def fmt_dt(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        g = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"][dt.weekday()]
        return f"{g} {dt.day} {MESI[dt.month][:3]} · {dt.strftime('%H:%M')}"
    except Exception:
        return "Oggi"
def render_frames(matches, hook_text, frames_dir):
    os.makedirs(frames_dir, exist_ok=True)
    bg = draw_base_bg()
    now = datetime.now()
    date_label = f"{GIORNI[now.weekday()]} {now.day} {MESI[now.month]} {now.year}"
    total_frames, cta_start = int(FPS * DUR), int(FPS * 10.8)

    for f_idx in range(total_frames):
        t, frame = f_idx / FPS, bg.copy()
        d = ImageDraw.Draw(frame, "RGBA")

        if f_idx < cta_start:
            d.text((64, 72), "352 PRONOSTICI · RADAR AI", font=F_TAG, fill=(16, 185, 129))
            d.text((64, 112), date_label, font=F_DATE, fill=(148, 163, 184))
            d.line((64, 156, 260, 156), fill=(245, 158, 11), width=5)
            d.multiline_text((64, 182), hook_text, font=F_HOOK, fill=(241, 245, 249), spacing=12)

            for idx, m in enumerate(matches):
                appear_t = 0.6 + idx * 1.6
                if t < appear_t:
                    continue
                ease = 1 - (1 - min(1.0, (t - appear_t) / 1.1)) ** 3
                y0, x0, x1 = 370 + idx * 440, 56, W - 56
                d.rounded_rectangle((x0, y0, x1, y0 + 395), radius=32, fill=(19, 28, 49, 240), outline=(45, 62, 95, 200), width=3)

                d.ellipse((90, y0 + 30, 134, y0 + 74), fill=(16, 185, 129))
                d.text((104, y0 + 38), str(idx + 1), font=F_BADGE, fill=(11, 17, 32))
                comp = (m.get("comp") or m.get("competizione") or "Calcio")[:26]
                d.text((152, y0 + 39), f"{fmt_dt(m.get('data', ''))} · {comp}", font=F_META, fill=(148, 163, 184))
                d.rounded_rectangle((x1 - 125, y0 + 28, x1 - 32, y0 + 68), radius=18, fill=(16, 185, 129, 45), outline=(16, 185, 129, 180), width=2)
                d.text((x1 - 102, y0 + 36), "TOP", font=F_BADGE, fill=(52, 211, 153))

                d.text((90, y0 + 98), (m.get("casa") or "Casa")[:22], font=F_TEAM, fill=(248, 250, 252))
                d.text((90, y0 + 148), (m.get("trasf") or "Ospite")[:22], font=F_TEAM, fill=(248, 250, 252))

                pp = m.get("pronostico_principale") or {}
                esito, target_pct = str(pp.get("esito") or "1X"), int(float(pp.get("probabilita") or 80))
                cur_pct = int(target_pct * ease)
                d.text((90, y0 + 216), f"Consigliato · {esito}", font=F_PICK, fill=(251, 191, 36))
                pct_str = f"{cur_pct}%"
                d.text((x1 - 40 - d.textlength(pct_str, font=F_PCT), y0 + 198), pct_str, font=F_PCT, fill=(16, 185, 129))

                bx0, bx1, by = 90, x1 - 40, y0 + 278
                d.rounded_rectangle((bx0, by, bx1, by + 16), radius=8, fill=(30, 41, 59))
                fill_w = int((bx1 - bx0) * (cur_pct / 100.0))
                if fill_w > 12:
                    d.rounded_rectangle((bx0, by, bx0 + fill_w, by + 16), radius=8, fill=(16, 185, 129))

                aff = int(float(m.get("indice_affidabilita") or target_pct))
                d.text((90, y0 + 322), f"Indice affidabilità {aff}%", font=F_SUB, fill=(148, 163, 184))
                r_txt = "38+ Mercati AI · Dati Reali"
                d.text((x1 - 40 - d.textlength(r_txt, font=F_SUB), y0 + 322), r_txt, font=F_SUB, fill=(100, 116, 139))

            d.rounded_rectangle((56, H - 150, W - 56, H - 64), radius=24, fill=(19, 28, 49, 220), outline=(45, 62, 95, 160), width=2)
            ft_txt = "Analisi completa gratis sull'app · Solo 18+"
            d.text(((W - d.textlength(ft_txt, font=F_PICK)) / 2, H - 124), ft_txt, font=F_PICK, fill=(226, 232, 240))
        else:
            pulse = 1.0 + 0.03 * math.sin(((f_idx - cta_start) / FPS) * 7.0)
            d.rounded_rectangle((64, 340, W - 64, 1540), radius=44, fill=(19, 28, 49, 245), outline=(16, 185, 129, 220), width=4)
            d.rounded_rectangle((W // 2 - 140, 430, W // 2 + 140, 520), radius=26, fill=(16, 185, 129, 40), outline=(16, 185, 129), width=3)
            d.text(((W - d.textlength("APP UFFICIALE", font=F_TAG)) / 2, 460), "APP UFFICIALE", font=F_TAG, fill=(52, 211, 153))
            d.text(((W - d.textlength("352 PRONOSTICI", font=F_CTA_TITLE)) / 2, 585), "352 PRONOSTICI", font=F_CTA_TITLE, fill=(248, 250, 252))

            for li, line in enumerate(["Tutte le partite di oggi,", "38+ mercati statistici AI", "e il Radar Sorprese in tempo reale."]):
                d.text(((W - d.textlength(line, font=F_CTA_SUB)) / 2, 710 + li * 54), line, font=F_CTA_SUB, fill=(148, 163, 184))

            btn_w, btn_h = int(820 * pulse), int(124 * pulse)
            bx0, by0 = (W - btn_w) // 2, 980 - (btn_h - 124) // 2
            d.rounded_rectangle((bx0, by0, bx0 + btn_w, by0 + btn_h), radius=34, fill=(16, 185, 129))
            btn_txt = "APRI L'APP GRATUITA  ↗"
            d.text(((W - d.textlength(btn_txt, font=F_CTA_BTN)) / 2, by0 + (btn_h - 38) // 2), btn_txt, font=F_CTA_BTN, fill=(11, 17, 32))

            bio_txt = "Trovi il link diretto nella BIO del profilo"
            d.text(((W - d.textlength(bio_txt, font=F_PICK)) / 2, 1180), bio_txt, font=F_PICK, fill=(251, 191, 36))
            disc_txt = "18+ · Contenuto informativo e statistico"
            d.text(((W - d.textlength(disc_txt, font=F_SUB)) / 2, 1430), disc_txt, font=F_SUB, fill=(100, 116, 139))

        frame.save(os.path.join(frames_dir, f"f_{f_idx:04d}.png"))

def main():
    matches, hook = get_matches(), random.choice(HOOKS)
    frames_dir, wav_path = os.path.join(OUT_DIR, "frames"), os.path.join(OUT_DIR, "bg.wav")
    mp4_path, cap_path = os.path.join(OUT_DIR, "tiktok_daily.mp4"), os.path.join(OUT_DIR, "tiktok_caption.txt")
    render_frames(matches, hook, frames_dir)
    make_audio(wav_path)
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f_%04d.png"), "-i", wav_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-c:a", "aac", "-b:a", "128k", "-shortest", mp4_path], check=True)
    with open(cap_path, "w", encoding="utf-8") as f:
        f.write(f"{random.choice(CAPTIONS)}\n\n#calcio #statistichecalcio #championsleague #seriea #analisitattica #352pronostici")
    print("Video TikTok generato con successo:", mp4_path)

if __name__ == "__main__":
    main()
