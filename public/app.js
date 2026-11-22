'use strict';

/* =====================================================================
   CONFIGURAZIONE VIP (modifica solo qui)
   ===================================================================== */
// Link di pagamento: sostituisci con il TUO link personale, es. 'https://revolut.me/tuousername'
const VIP_PAY_URL = '';

// Revolut.me: se il link richiede l'importo in CENTESIMI (es. 499 invece di 4.99) imposta true
const REVOLUT_CENTS = false;

const VIP_MAIL = 'info.hubcorsi@gmail.com';
// Piani in vendita (i giorni devono coincidere con le chiavi di VIP_CODES)
// amount = importo numerico in euro passato al link Revolut; cause = causale copiabile
const VIP_PLANS = [
  { days: 7, name: 'Pass Settimanale', price: '4,99 €', amount: 4.99, cause: 'VIP Settimanale 352', note: '7 giorni', sub: '≈ 0,71 € al giorno' },
  { days: 30, name: 'Pass Mensile', price: '14,99 €', amount: 14.99, cause: 'VIP Mensile 352', note: '30 giorni', sub: '≈ 0,50 € al giorno', tag: 'Più Scelto' },
  { days: 365, name: 'Pass Annuale', price: '49,99 €', amount: 49.99, cause: 'VIP Annuale 352', note: '365 giorni', sub: '≈ 4,17 € al mese · risparmi il 72% rispetto al mensile', tag: 'Miglior Valore' }
];
// Codici Pass salvati come hash SHA-256 (il codice in chiaro NON compare qui).
// Per aggiungerne uno: calcola SHA-256 di  352p|CODICE  (maiuscolo) e incollalo nella lista giusta.
const VIP_SALT = '352p|';
const VIP_CODES = {
  7: ['68b67960044a320604bb8a244ee3637f03d4c7ee68bee616b0fb18e8246b751a', 'eb3158f294ab66ee1009235abb2c058b542f0eeaeb0e6b5d05461126f9c4d2a0', '0355dad0ac77686e93ac40ce703bccfd0f6f1da94f300ae8fc2e7980f81925ac', 'd2fc3cdf9fa14d4cd6f93abcf582ccf3b9cb1e7e47eec25a4490c53e5fe6dabc', 'e91f31c9a087bb13f3053e24c7c3e3b12256f9429311fdb91e6d862ef4a11658'],
  30: ['a043510a893e004d90d1766b0806f8209e1f58b0d5ae8fc4570239f03fd8a443', 'a6f436d48d997db733804cea5a4d4967f44e847c72bc64f257b85fc79425bf0c', 'c1b22ed0cecafb24dff1da7a54cf27f566d89a551892fadddb9cb36485c241b5', 'f32b01011a3ce1d039bf6cf891c02f464458fac8c4487f7966c640941eff3d96', '0a221d2235d42dba70be41e58a7c51fb61121436f9206ced6767be14e3ee22ef'],
  365: ['ab60407431a4d26e5235e2da46a59b9a0d4d7ebe3ac6d12a746f55730de68687', 'fa1c00597b3272b22c749402cf934490b1727c7826946c9e97806b3f4240c4df', 'a279967e56e61c4b6149383e9816e0292779d200c5e68f2060106ac83ee2b47e', 'a42fccbd856e80a276526cb14492bbaa9cdb3d0fafcc254e0250ffa72857dcc8', '890ac5187e726282f1f10ebd8a82e637ebc2cecf4ee6d2765ef39bbda5522b12']
};
// Admin Creatore: VIP permanente. Sblocco rapido: apri l'app con  ?vip=<codice>  (l'URL viene ripulito).
const VIP_ADMIN_HASH = 'cf12e2e0c2aeaa57d6d723d4a94b63c5c036e5633fd64cf718cfba665c4f985f';
// Limiti utente Standard (reset ogni giorno)
const FREE = { matches: 10, gen: 3, swap: 3, saved: 3 };

const $ = s => document.querySelector(s), L = localStorage;
const J = (k, d) => { try { return JSON.parse(L[k]) ?? d } catch { return d } };
// Compliance editoriale: nessun riferimento a scommesse, quote, bookmaker, puntate o denaro
const FORB = /\b(bet\w*|scommess\w*|quot[ae]|bookmaker\w*|puntat\w*|odds?|stake|euro|denaro|soldi|jackpot)\b|[€$£]/i;
const E = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const clean = s => { s = String(s ?? ''); return FORB.test(s) ? (s.match(/[^.!?]+[.!?]*/g) || []).filter(p => !FORB.test(p)).join(' ') : s };
const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const ic = (n, c = '') => `<svg class="ic ${c}"><use href="#i-${n}"/></svg>`;
// Indirizzo pubblico dell'app (GitHub Pages) usato nelle condivisioni
const siteUrl = () => location.href.split('#')[0].split('?')[0];
let D = [], meta = '', fav = J('fav', []), F = { c: '', f: false, t: false, tm: false, top: false, res: false, q: '' }, tab = 'home', out = null, POOL = [], cardUrl = '', cardBlob = null, topOpen = false, vipSel = null, liveOnly = false, winF = 'all', simStd = false, storyUrl = '', storyBlob = null, liveT = null, liveCd = 50, flash = {};
const openG = new Set();   // gruppi di campionati espansi (menu +/−)
let G = { n: 5, m: ['1X2', 'DC', 'UO', 'GN', 'MG', 'CB', 'DNB', 'SQ', 'TM'], best: false, risk: 'all', day: 'all', one: '' };

const GR = {
  '1X2': ['1', 'X', '2'],
  DC: ['1X', 'X2', '12'],
  DNB: ['DNB 1', 'DNB 2', 'Win 0 Casa', 'Win 0 Trasf'],
  UO: ['U1.5', 'O1.5', 'U2.5', 'O2.5', 'U3.5', 'O3.5', 'U4.5', 'O4.5'],
  GN: ['GG', 'NG'],
  MG: ['MG1-2', 'MG1-3', 'MG2-3', 'MG2-4', 'MG2-5', 'MG3-5'],
  SQ: ['Casa O0.5', 'Casa O1.5', 'Trasf O0.5', 'Trasf O1.5', 'Clean Sheet 1', 'Clean Sheet 2', 'MG Casa 1-2', 'MG Trasf 1-2'],
  TM: ['1T 1', '1T X', '1T 2', '1T O0.5', '1T U0.5', '1T O1.5', '2T O0.5', 'Gol Entrambi Tempi'],
  CB: ['1+O1.5', '1+O2.5', '2+O1.5', '2+O2.5', '1X+O1.5', 'X2+O1.5', '1X+GG', 'X2+GG', 'GG+O2.5', '1+GG', '2+GG', '2+U3.5'],
  MARC: ['MARC']
};
const GL = { '1X2': '1X2', DC: 'Doppia Chance', DNB: 'Rimborso & Win 0', UO: 'Under/Over', GN: 'Gol/NoGol', MG: 'Multigol', SQ: 'Gol Squadre & CS', TM: '1° e 2° Tempo', CB: 'Combo', MARC: 'Marcatore' };
const lbl = k => {
  if (k.startsWith('Segna ')) return k;
  return ({ '1': 'Esito 1', X: 'Esito X', '2': 'Esito 2', GG: 'Goal (GG)', NG: 'NoGoal (NG)', 'DNB 1': 'Rimborso Parità 1', 'DNB 2': 'Rimborso Parità 2', 'Win 0 Casa': 'Casa Vince a Zero', 'Win 0 Trasf': 'Trasf Vince a Zero', 'Clean Sheet 1': 'Casa Non Subisce', 'Clean Sheet 2': 'Trasf Non Subisce', 'Gol Entrambi Tempi': 'Gol in 1° e 2° Tempo' }[k])
    || k.replace(/^1T /, '1° Tempo ').replace(/^2T /, '2° Tempo ').replace(/U(?=\d)/g, 'Under ').replace(/O(?=\d)/g, 'Over ').replace('MG', 'Multigol ');
};

const mk = m => {
  const b = { ...(m.prob_1x2 || {}), ...(m.mercatI_completi || m.mercat_completi || m.mercati_completi || {}) };
  const p1 = +b['1'] || 35, px = +b['X'] || 28, p2 = +b['2'] || 37, o25 = +b['O2.5'] || 50, gg = +b['GG'] || 50;
  const lh = Math.max(0.25, (o25 / 50) * (p1 / 45) * 1.35), la = Math.max(0.2, (o25 / 50) * (p2 / 45) * 1.15);
  const pois = (l, k) => { let f = 1; for (let i = 2; i <= k; i++) f *= i; return Math.exp(-l) * Math.pow(l, k) / f; };
  const pct = x => Math.max(4, Math.min(94, Math.round(x * 100)));
  const cs1 = pois(la, 0), cs2 = pois(lh, 0);
  const extra = {
    'DNB 1': Math.round((p1 / Math.max(1, p1 + p2)) * 100), 'DNB 2': Math.round((p2 / Math.max(1, p1 + p2)) * 100),
    'Win 0 Casa': pct((p1 / 100) * cs1 * 1.25), 'Win 0 Trasf': pct((p2 / 100) * cs2 * 1.25),
    'U4.5': Math.min(96, Math.round((+b['U3.5'] || 78) + 12)), 'O4.5': Math.max(4, 100 - Math.min(96, Math.round((+b['U3.5'] || 78) + 12))),
    'MG2-5': Math.min(88, Math.round((+b['MG2-4'] || 52) + 14)),
    'Casa O0.5': pct(1 - cs2), 'Casa O1.5': pct(1 - cs2 - pois(lh, 1)),
    'Trasf O0.5': pct(1 - cs1), 'Trasf O1.5': pct(1 - cs1 - pois(la, 1)),
    'Clean Sheet 1': pct(cs1), 'Clean Sheet 2': pct(cs2),
    'MG Casa 1-2': pct(pois(lh, 1) + pois(lh, 2)), 'MG Trasf 1-2': pct(pois(la, 1) + pois(la, 2)),
    '1T 1': pct((p1 / 100) * 0.68), '1T X': pct(0.42), '1T 2': pct((p2 / 100) * 0.66),
    '1T O0.5': pct(1 - pois((lh + la) * 0.44, 0)), '1T U0.5': pct(pois((lh + la) * 0.44, 0)),
    '1T O1.5': pct(1 - pois((lh + la) * 0.44, 0) - pois((lh + la) * 0.44, 1)),
    '2T O0.5': pct(1 - pois((lh + la) * 0.56, 0)),
    'Gol Entrambi Tempi': pct((1 - pois((lh + la) * 0.44, 0)) * (1 - pois((lh + la) * 0.56, 0)))
  };
  return { ...extra, ...b };
};

const LV = s => s === 'IN_PLAY' || s === 'PAUSED';
const day = m => new Date(m.data).toLocaleDateString('sv');
const tm = m => new Date(m.data).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
// dlab(d) = "sabato 21 novembre"; dlab(d, true) = "sab 21 nov" (versione breve per le card)
const dlab = (d, sh) => new Date(d + 'T12:00').toLocaleDateString('it-IT', sh ? { weekday: 'short', day: 'numeric', month: 'short' } : { weekday: 'long', day: 'numeric', month: 'long' });
const col = v => v >= 75 ? '#10B981' : v >= 60 ? '#F59E0B' : '#EF4444';   // scala cromatica affidabilita
const num = v => Math.max(0, Math.min(100, Math.round(+v || 0)));
const todayK = () => new Date().toLocaleDateString('sv');
const tmrK = () => { const d = new Date(); d.setDate(d.getDate() + 1); return d.toLocaleDateString('sv') };

/* ---------- Nomi reali: scarta segnaposto generici dell'AI ---------- */
const GENERIC_RX = /\b(marcator\w*|attaccant\w*|centrocampist\w*|difensor\w*|esterno|esterni|casa|trasferta|giocator\w*)\b/;
const isNomeReale = s => {
  const n = norm(String(s ?? '')).trim();
  return n.length > 2 && /[a-z]/.test(n) && !GENERIC_RX.test(n) && !/^(n\/?a|tbd|sconosciuto|non disponibile)$/.test(n);
};
const pls = a => (Array.isArray(a) ? a : []).filter(p => p && isNomeReale(p.giocatore));

/* ---------- Big Match ---------- */
const BIG_RX = /internazionale|\binter\b|\bmilan\b|napoli|\broma\b|lazio|juventus|atalanta|real madrid|barcelona|atletico|manchester (city|united)|liverpool|arsenal|chelsea|tottenham|bayern|dortmund|leverkusen|paris saint|marseille|benfica|\bporto\b|sporting clube|ajax/;
const isBig = m => m.comp !== 'BSA' && BIG_RX.test(norm(m.casa)) && BIG_RX.test(norm(m.trasf));
const isTop = m => Object.values(mk(m)).some(v => v >= 80);

/* ---------- Esito pronostico (✓ / ✗) e statistiche verificate ---------- */
function evTerm(t, h, a) {
  const g = h + a;
  if (t === '1') return h > a; if (t === 'X') return h === a; if (t === '2') return a > h;
  if (t === '1X') return h >= a; if (t === 'X2') return a >= h; if (t === '12') return h !== a;
  if (t === 'GG') return h > 0 && a > 0; if (t === 'NG') return !(h > 0 && a > 0);
  let r = /^([UO])(\d)\.5$/.exec(t); if (r) return r[1] === 'U' ? g < +r[2] + .5 : g > +r[2] + .5;
  r = /^MG(\d)-(\d)$/.exec(t); if (r) return g >= +r[1] && g <= +r[2];
  return null;
}
// true = centrato, false = mancato, null = non valutabile
function evalEsito(esito, score) {
  if (!esito || !Array.isArray(score) || score[0] == null || score[1] == null) return null;
  const h = +score[0], a = +score[1]; if (isNaN(h) || isNaN(a)) return null;
  const rs = String(esito).toUpperCase().replace(/\s+/g, '').split('+').map(t => evTerm(t, h, a));
  return rs.includes(null) ? null : rs.every(Boolean);
}
const esitoOf = m => (m.stato === 'FINISHED' && m.pronostico_principale) ? evalEsito(m.pronostico_principale.esito, m.score) : null;
// Lo storico verificato si accumula in localStorage cosi' non si perde quando le partite escono dalla finestra dei 3 giorni
function histSync() {
  const h = J('hist', {}); let ch = false; const lim = Date.now() - 400 * 864e5;
  D.forEach(m => { const r = esitoOf(m); if (r === null) return; const k = String(m.id); if (!h[k]) { h[k] = { r: r ? 1 : 0, d: day(m) }; ch = true } });
  for (const k in h) if (new Date(h[k].d) < lim) { delete h[k]; ch = true }
  if (ch) L.hist = JSON.stringify(h);
}
const histStats = () => { const v = Object.values(J('hist', {})), x = v.filter(o => o.r).length; return { x, y: v.length, p: v.length ? Math.round(x * 100 / v.length) : 0 } };

/* ---------- Freemium / VIP ---------- */
const isAdmin = () => L.vipAdmin === '1';
const sha = async c => { try { const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(VIP_SALT + String(c).trim().toUpperCase().replace(/\s+/g, ''))); return [...new Uint8Array(b)].map(v => v.toString(16).padStart(2, '0')).join('') } catch { return '' } };
const isVip = () => !simStd && (isAdmin() || +L.vipExp > Date.now());
const vipLeft = () => {
  const ms = +L.vipExp - Date.now(); if (!(ms > 0)) return '';
  const d = Math.floor(ms / 864e5), h = Math.floor(ms % 864e5 / 36e5), mi = Math.floor(ms % 36e5 / 6e4);
  return d > 0 ? `${d} ${d == 1 ? 'giorno' : 'giorni'} e ${h} ${h == 1 ? 'ora' : 'ore'}` : `${h} ${h == 1 ? 'ora' : 'ore'} e ${mi} min`;
};
// contatori giornalieri: si azzerano da soli quando cambia la data
const dget = (k, def) => { const o = J(k, null); return o && o.d === todayK() ? o : { d: todayK(), ...def } };
const dput = (k, o) => { L[k] = JSON.stringify(o) };
const genLeft = () => Math.max(0, FREE.gen - dget('gc', { n: 0, s: 0 }).n);
const swapLeft = () => Math.max(0, FREE.swap - dget('gc', { n: 0, s: 0 }).s);
const VIPMSG = {
  match: `Hai raggiunto il limite giornaliero di ${FREE.matches} pronostici gratuiti! Passa a 352 VIP per sbloccare tutte le analisi senza limiti, il Generatore Pro e zero pubblicità`,
  gen: `Hai raggiunto il limite giornaliero di ${FREE.gen} generazioni gratuite! Passa a 352 VIP per sbloccare generazioni illimitate, il Generatore Pro e zero pubblicità`,
  swap: `Hai usato i ${FREE.swap} cambi evento gratuiti di oggi! Passa a 352 VIP per cambiare evento senza limiti, il Generatore Pro e zero pubblicità`,
  save: `Hai raggiunto il limite di ${FREE.saved} combinazioni salvate gratuite! Passa a 352 VIP per salvarne senza limiti, il Generatore Pro e zero pubblicità`
};
function showVip(reason) { $('#vipmsg').textContent = VIPMSG[reason] || VIPMSG.match; $('#vipm').classList.add('open'); tap(300) }
// Limite 10 partite/giorno: riaprire una gara gia' sbloccata oggi non consuma slot
function gateMatch(m) {
  if (isVip()) return true;
  const u = dget('unl', { ids: [] });
  if (u.ids.includes(m.id)) return true;
  if (u.ids.length >= FREE.matches) { showVip('match'); return false }
  u.ids.push(m.id); dput('unl', u); return true;
}

/* ---------- Feedback: vibrazione e micro-suoni ---------- */
const fx = () => L.fx !== '0';
let AC; const beep = f => { if (!fx()) return; try { AC = AC || new (window.AudioContext || window.webkitAudioContext)(); const o = AC.createOscillator(), g = AC.createGain(); o.frequency.value = f || 660; g.gain.value = .04; o.connect(g); g.connect(AC.destination); o.start(); o.stop(AC.currentTime + .06) } catch { } };
const tap = f => { if (fx()) { try { navigator.vibrate?.(15) } catch { } beep(f) } };
const toast = s => { const e = $('#toast'); e.textContent = s; e.classList.add('on'); setTimeout(() => e.classList.remove('on'), 1800) };
async function share(text, url) { if (navigator.share) { try { await navigator.share({ title: '352 Pronostici', text, url }); return true } catch { return false } } try { await navigator.clipboard.writeText(url ? text + '\n' + url : text); toast('Copiato!'); return true } catch { return false } }

/* ---------- Scudetti SVG (colori e pattern reali, niente loghi protetti) ---------- */
const PAL = ['#1d4ed8', '#b91c1c', '#047857', '#7c3aed', '#b45309', '#0e7490'];
const isHex = c => /^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(c || '');
const lum = h => { h = h.replace('#', ''); if (h.length == 3) h = [...h].map(x => x + x).join(''); const [r, g, b] = [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16) / 255).map(v => v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4); return .2126 * r + .7152 * g + .0722 * b };
function sInfo(name, st) {
  const c = (st?.colori || []).filter(isHex), h = [...name].reduce((a, x) => (a * 31 + x.charCodeAt(0)) % 997, 0);
  const c1 = c[0] || PAL[h % 6], c2 = c[1] || '#f8fafc', p = ['vertical', 'horizontal', 'diagonal', 'half', 'solid'].includes(st?.pattern) ? st.pattern : 'solid';
  const cen = p === 'solid' ? lum(c1) : p === 'half' ? (lum(c1) + lum(c2)) / 2 : lum(c2);
  return { c1, c2, p, tc: cen > .45 ? '#0B1120' : '#ffffff', sig: name.normalize('NFD').replace(/[^A-Za-z ]/g, '').trim().slice(0, 3).toUpperCase() };
}
let sid = 0;
function scudetto(name, st, s = 40) {
  const { c1, c2, p, tc, sig } = sInfo(name, st), id = 'sc' + (++sid), R = (x, y, w, h, f) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${f}"/>`;
  const body = { vertical: R(0, 0, 40, 46, c1) + R(14.3, 0, 11.4, 46, c2), horizontal: R(0, 0, 40, 46, c1) + R(0, 17, 40, 14, c2), diagonal: R(0, 0, 40, 46, c1) + `<polygon points="34,-4 56,-4 -4,56 -4,34" fill="${c2}"/>`, half: R(0, 0, 20, 46, c1) + R(20, 0, 20, 46, c2), solid: R(0, 0, 40, 46, c1) }[p];
  return `<svg width="${s}" height="${Math.round(s * 1.15)}" viewBox="0 0 40 46" aria-hidden="true"><defs><clipPath id="${id}"><path d="M3 3h34v21c0 11-8 17-17 20C11 41 3 35 3 24z"/></clipPath></defs><g clip-path="url(#${id})">${body}<rect x="3" y="3" width="34" height="8" fill="#000" opacity=".12"/></g><path d="M3 3h34v21c0 11-8 17-17 20C11 41 3 35 3 24z" fill="none" stroke="${p === 'solid' ? c2 : 'rgba(255,255,255,.55)'}" stroke-width="2"/><text x="20" y="28" text-anchor="middle" font-size="${sig.length > 2 ? 12 : 14}" font-weight="800" fill="${tc}" font-family="Plus Jakarta Sans,sans-serif">${E(sig)}</text></svg>`;
}

/* ---------- Grafici SVG ---------- */
function ring(p, s = 84, w = 9) {
  p = num(p); const r = (s - w) / 2, c = 2 * Math.PI * r, k = s / 2;
  return `<svg class="ring" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}" style="--c:${c.toFixed(1)};--p:${p}"><circle cx="${k}" cy="${k}" r="${r}" fill="none" stroke="currentColor" stroke-opacity=".18" stroke-width="${w}"/><circle class="rf" cx="${k}" cy="${k}" r="${r}" fill="none" stroke="${col(p)}" stroke-width="${w}" stroke-linecap="round" transform="rotate(-90 ${k} ${k})"/><text x="${k}" y="${k}" text-anchor="middle" dominant-baseline="central" font-weight="800" font-size="${Math.round(s * .26)}" fill="currentColor">${p}%</text></svg>`;
}
const gauge = p => { p = num(p); return `<div><svg class="gauge" viewBox="0 0 120 72" style="--p:${p}"><path d="M10 62A50 50 0 0 1 110 62" fill="none" stroke="currentColor" stroke-opacity=".15" stroke-width="11" stroke-linecap="round"/><path class="gf" d="M10 62A50 50 0 0 1 110 62" fill="none" stroke="${col(p)}" stroke-width="11" stroke-linecap="round" pathLength="100"/><text x="60" y="58" text-anchor="middle" font-size="26" font-weight="800" fill="currentColor">${p}</text></svg><div class="leg"><span><i style="background:#EF4444"></i>&lt;60</span><span><i style="background:#F59E0B"></i>60-74</span><span><i style="background:#10B981"></i>75+</span></div></div>` };
const bar = segs => `<div class="pb"><div class="pl">${segs.map(s => `<span><i style="background:${s.c}"></i>${s.l} ${num(s.v)}%</span>`).join('')}</div><div class="pt">${segs.map(s => `<b style="--w:${num(s.v)}%;background:${s.c}">${s.v >= 14 ? num(s.v) + '%' : ''}</b>`).join('')}</div></div>`;
function pitch(m) {
  const f = m.formazioni || {}; if (!f.casa && !f.trasferta) return '';
  const side = (lato, left, st) => {
    const x = f[lato]; if (!x) return ''; const mods = String(x.modulo || '').split('-').map(Number).filter(n => n > 0 && n < 9), rows = [1, ...mods], names = x.undici || [], si = sInfo(lato === 'casa' ? m.casa : m.trasf, st); let i = 0, s = '';
    rows.forEach((n, r) => { const px = left ? 18 + r * (116 / rows.length) : 300 - (18 + r * (116 / rows.length)); for (let j = 0; j < n; j++) { const py = (j + 1) * 190 / (n + 1), nm = names[i++], sn = nm ? nm.split(' ').pop().slice(0, 9) : ''; s += `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="7" fill="${si.c1}" stroke="${si.c2}" stroke-width="2"/>${sn ? `<text x="${px.toFixed(1)}" y="${(py + 16).toFixed(1)}" text-anchor="middle" font-size="7.5" font-weight="700" fill="#fff" stroke="#000a" stroke-width=".4" paint-order="stroke">${E(sn)}</text>` : ''}` } });
    return s + `<text x="${left ? 8 : 292}" y="12" text-anchor="${left ? 'start' : 'end'}" font-size="9" font-weight="800" fill="#fff" opacity=".85">${E(x.modulo || '')}</text>`;
  };
  return `<svg class="pitch" viewBox="0 0 300 190"><rect width="300" height="190" fill="#0f5132"/><g fill="none" stroke="#fff" stroke-opacity=".4" stroke-width="1.2"><rect x="3" y="3" width="294" height="184"/><path d="M150 3v184"/><circle cx="150" cy="95" r="22"/><rect x="3" y="55" width="36" height="80"/><rect x="261" y="55" width="36" height="80"/></g>${side('casa', true, m.stemma_casa)}${side('trasferta', false, m.stemma_trasf)}</svg>`;
}

/* ---------- La Mia Lista (localStorage: 'lst' = array di id partita) ---------- */
const inLst = id => J('lst', []).includes(+id);
const lbT = on => on ? '✓ Nella lista' : '+ Aggiungi alla lista';
const lbBtn = (m, x = '') => `<button class="lb ${x} ${inLst(m.id) ? 'on' : ''}" data-a="lst" data-v="${m.id}">${lbT(inLst(m.id))}</button>`;
const lstItems = () => J('lst', []).map(id => D.find(m => m.id == id)).filter(Boolean);
let lcardUrl = '';

function lstText(withUrl = true) {
  const it = lstItems();
  const rows = it.map((m, i) => { const pp = m.pronostico_principale; return `${i + 1}. ${m.casa} - ${m.trasf} (${dlab(day(m), true)} ${tm(m)})${pp ? `: ${pp.esito} ${num(pp.probabilita)}%` : ''}${m.affidabilita != null ? ` · aff. ${num(m.affidabilita)}%` : ''}` });
  return '352 Pronostici - La mia lista\n' + rows.join('\n') + '\n18+ · Solo informativo e statistico.' + (withUrl ? '\n' + siteUrl() : '');
}
function vList() {
  const it = lstItems();
  if (!it.length) return `<div class="empty">${ic('list')}<b style="display:block;color:var(--tx);font-family:var(--fh)">La tua lista è vuota</b><p style="font-size:13px;margin-top:4px">Tocca “+ Aggiungi alla lista” su una partita per raccoglierla qui.</p></div>` + disc();
  const rel = it.filter(m => m.affidabilita != null), avg = rel.length ? Math.round(rel.reduce((s, m) => s + num(m.affidabilita), 0) / rel.length) : 0;
  const pr = it.filter(m => m.pronostico_principale), pc = pr.length ? (pr.reduce((a, m) => a * num(m.pronostico_principale.probabilita) / 100, 1) * 100).toFixed(1) : null;
  return `<div class="lhead">${ring(avg, 84, 9)}<div><h3>Indice di Affidabilità Combinata</h3><p>Media dell’affidabilità di ${rel.length} ${rel.length == 1 ? 'selezione' : 'selezioni'}${pc !== null ? `.<br>Probabilità combinata stimata: <b style="color:var(--tx)">${pc}%</b>` : ''}</p></div></div>`
    + it.map(m => {
      const pp = m.pronostico_principale, ev = esitoOf(m);
      return `<div class="li" data-a="open" data-v="${m.id}"><div class="pz">${scudetto(m.casa, m.stemma_casa, 26)}${scudetto(m.trasf, m.stemma_trasf, 26)}<span class="tn">${E(m.casa)} - ${E(m.trasf)}</span></div>
<div class="lr">${pp ? `<span class="bdg" style="--bc:${col(pp.probabilita)}">${ev !== null ? (ev ? '✓ ' : '✗ ') : ''}${E(pp.esito)} · ${num(pp.probabilita)}%</span>` : ''}</div>
<div class="meta"><span>${E(m.compNome)}</span><span>${E(dlab(day(m), true))} · ${tm(m)}</span>${m.affidabilita != null ? `<span style="color:${col(num(m.affidabilita))};font-weight:700">Affidabilità ${num(m.affidabilita)}%</span>` : ''}${m.score ? `<span><b>${m.score.join(' - ')}</b></span>` : ''}</div>
<button class="lx" data-a="lrm" data-v="${m.id}" aria-label="Rimuovi dalla lista">✕</button></div>`;
    }).join('')
       + `<div class="lshare"><button class="btn wa" data-a="lwa">Condividi su WhatsApp</button><button class="btn tg" data-a="ltg">Condividi su Telegram</button></div><button class="btn" data-a="lmkcard">${ic('img')}Crea Card Immagine della Lista</button><div id="lcardout">${lcardUrl ? `<img class="cimg" src="${lcardUrl}" alt="Card Lista 352"><button class="btn s" data-a="ldl">${ic('down')}Scarica Immagine</button>` : ''}</div>` + disc();

}

/* ---------- Selezioni Top del Giorno (>= 80%) ---------- */
function topSel() {
  const up = D.filter(m => m.stato !== 'FINISHED' && m.prob_1x2); if (!up.length) return '';
  const d0 = up.map(day).sort()[0];
  const it = up.filter(m => day(m) === d0).map(m => { let b = null; for (const [x, v] of Object.entries(mk(m))) { const n = +v; if (n >= 80 && (!b || n > b.v)) b = { x, v: Math.round(n) } } return b ? { m, ...b } : null }).filter(Boolean).sort((a, b) => b.v - a.v).slice(0, 3);
  if (!it.length) return '';
  const vip = isVip(), lab = d0 === todayK() ? 'Oggi' : d0 === tmrK() ? 'Domani' : dlab(d0, true);
  return `<div class="tsb"><div class="ch">${ic('flame')}Selezioni Top del Giorno · ${E(lab)} · 80%+</div>` + it.map((o, i) => (i === 0 || vip)
    ? `<div class="ts" data-a="open" data-v="${o.m.id}"><span class="rk">${i + 1}</span><div class="pz">${scudetto(o.m.casa, o.m.stemma_casa, 24)}${scudetto(o.m.trasf, o.m.stemma_trasf, 24)}<span class="tn">${E(o.m.casa)} - ${E(o.m.trasf)}</span></div><span class="bdg" style="--bc:${col(o.v)}">${E(lbl(o.x))} · ${o.v}%</span></div>`
    : `<div class="ts lock" data-a="vipgo"><span class="rk">${i + 1}</span><div class="pz"><span class="blur" aria-hidden="true">●●●●●● - ●●●●●●</span></div><span class="lk">${ic('lock')}Sblocca con 352 VIP 💎</span></div>`).join('') + `</div>`;
}

/* ---------- Home ---------- */
const hay = m => norm([m.casa, m.trasf, ...pls(m.possibili_marcatori).map(p => p.giocatore), ...pls(m.possibili_ammoniti).map(p => p.giocatore), ...Object.values(m.formazioni || {}).flatMap(x => x.undici || [])].join(' '));
// ex = filtri da saltare (serve ai contatori: "quante partite avrei se attivassi questo filtro")
const isExpiredLive = m => LV(m.stato) && (Date.now() - Date.parse(m.data)) > 160 * 60 * 1000;
const isSurp = m => {
  const k = mk(m);
  return m.stato !== 'FINISHED' && !isExpiredLive(m) && ((+k['X2'] >= 62 && +k['1'] < 45) || +k['2'] >= 52 || (+k['GG'] >= 72 && +k['O2.5'] >= 65));
};

const vis = (ex = {}) => {
  const q = norm(F.q.trim()), td = todayK(), tr = tmrK();
  return D.filter(m => (!F.c || m.comp === F.c) && (!F.f || fav.includes(m.id)) && (ex.t || !F.t || day(m) === td) && (ex.tm || !F.tm || day(m) === tr) && (ex.top || !F.top || isTop(m)) && (ex.surp || !F.surp || isSurp(m)) && (!q || hay(m).includes(q)));
};

function colpo() {
  const m = D.filter(x => x.stato !== 'FINISHED' && x.affidabilita != null).sort((a, b) => b.affidabilita - a.affidabilita || (b.pronostico_principale?.probabilita || 0) - (a.pronostico_principale?.probabilita || 0))[0]; if (!m) return '';
  const pp = m.pronostico_principale || {};
  return `<div class="colpo" data-a="open" data-v="${m.id}"><div class="ch">${ic('flame')}Colpo del Giorno</div><div class="cr">${ring(m.affidabilita, 92)}<div class="cm"><div class="cp">${scudetto(m.casa, m.stemma_casa, 34)}<span>vs</span>${scudetto(m.trasf, m.stemma_trasf, 34)}</div><span class="tn">${E(m.casa)} - ${E(m.trasf)}</span>${pp.esito ? `<span class="bdg">${ic('zap')}${E(pp.esito)} · ${num(pp.probabilita)}%</span>` : ''}</div></div></div>`;
}
const tri = p => `<div class="tri"><div class="tb"><i style="flex:${num(p['1']) || 1};background:#10B981"></i><i style="flex:${num(p.X) || 1};background:#64748B"></i><i style="flex:${num(p['2']) || 1};background:#06B6D4"></i></div><div class="tl3"><span>1 · ${num(p['1'])}</span><span>X · ${num(p.X)}</span><span>2 · ${num(p['2'])}</span></div></div>`;
function card(m) {
   const lv = LV(m.stato) && !isExpiredLive(m), pp = m.pronostico_principale, ev = esitoOf(m), alta = pp && num(pp.probabilita) >= 75;

  return `<article class="card" data-a="open" data-v="${m.id}"><div class="ct"><span class="tn">${E(m.compNome)}</span>${isBig(m) ? '<span class="bm">★ Big Match</span>' : ''}</div><button class="fav ${fav.includes(m.id) ? 'on' : ''}" data-a="fav" data-v="${m.id}" aria-label="Preferita">${ic('heart')}</button>
<div class="mr"><div class="tz">${scudetto(m.casa, m.stemma_casa)}<span class="tn">${E(m.casa)}</span></div><div class="mc">${lv ? '<span class="live"><i></i>LIVE</span>' : ''}<span class="cdt">${E(dlab(day(m), true))}</span><b class="tt">${m.score ? m.score.join(' - ') : tm(m)}</b>${pp ? `<div class="pr">${ev !== null ? `<span class="eo ${ev ? 'ok' : 'ko'}" aria-label="${ev ? 'Pronostico centrato' : 'Pronostico mancato'}">${ev ? '✓' : '✗'}</span>` : ''}<span class="bdg" style="--bc:${col(pp.probabilita)}">${E(pp.esito)} · ${num(pp.probabilita)}%</span></div>${alta ? '<span class="hc">Alta confidenza</span>' : ''}` : ''}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf)}<span class="tn">${E(m.trasf)}</span></div></div>${m.prob_1x2 ? tri(m.prob_1x2) : ''}<div class="cta">${lbBtn(m)}<span class="cv">Visualizza pronostico${ic('chev')}</span></div></article>`;
}
function listHTML() {
  const l = vis(), ds = [...new Set(l.map(day))].sort(), td = todayK(), tr = tmrK(); let n = 0;
  const hl = d => d === td ? `Oggi <small>${dlab(d)}</small>` : d === tr ? `Domani <small>${dlab(d)}</small>` : dlab(d);
  return ds.length ? ds.map(d => `<h2 class="dh">${hl(d)}</h2>` + l.filter(m => day(m) === d).map(m => card(m) + (++n % 7 === 0 && !isVip() ? `<div class="ad-native" ${n === 7 ? 'id="ad-native-feed"' : ''} data-slot="${n / 7}"></div>` : '')).join('')).join('') : `<div class="empty">${ic('search')}</div>`;
}
const disc = () => `<div class="disc"><b>18+</b> Contenuti esclusivamente informativi e statistici: nessuna quota, nessun invito al gioco. Vietato ai minori di 18 anni.</div>`;
const chp = (on, a, v, i, t) => `<button class="chip ${on ? 'on' : ''}" data-a="${a}" ${v !== undefined ? `data-v="${v}"` : ''}>${i ? ic(i) : ''}${E(t)}</button>`;

/* Campionati raggruppati: il primo codice presente e' il "primario", gli altri i sotto-campionati (menu +/−).
   Adatta i codici ai valori reali di "comp" nel tuo matches.json; i codici non elencati finiscono comunque nei chip semplici. */
const LEAGUE_GROUPS = [
  { id: 'it', c: ['SA', 'SB', 'SC', 'CI'] },
  { id: 'en', c: ['PL', 'ELC', 'FAC', 'EFL'] },
  { id: 'es', c: ['PD', 'SD', 'CDR'] },
  { id: 'de', c: ['BL1', 'BL2', 'DFB'] },
  { id: 'fr', c: ['FL1', 'FL2', 'CDF'] },
  { id: 'eu', c: ['CL', 'EL', 'ECL'] }
];
function groupsInfo() {
  const pres = new Map(D.map(m => [m.comp, m.compNome])), used = new Set(), gs = [];
  LEAGUE_GROUPS.forEach(g => { const codes = g.c.filter(c => pres.has(c)); if (!codes.length) return; codes.forEach(c => used.add(c)); gs.push({ id: g.id, codes }) });
  return { pres, gs, rest: [...pres.keys()].filter(c => !used.has(c)) };
}
function leagueChips() {
  const { pres, gs, rest } = groupsInfo();
  let h = chp(!F.c, 'comp', '', '', 'Tutti');
  gs.forEach(g => {
    const m = g.codes[0], subs = g.codes.slice(1), open = openG.has(g.id);
    h += `<span class="cg ${F.c === m ? 'on' : ''} ${subs.includes(F.c) ? 'sub' : ''}"><button class="cgm" data-a="comp" data-v="${m}">${E(pres.get(m))}</button>${subs.length ? `<button class="cgp" data-a="gtog" data-v="${g.id}" aria-expanded="${open}" aria-label="${open ? 'Chiudi' : 'Apri'} sotto-campionati ${E(pres.get(m))}">${open ? '−' : '+'}</button>` : ''}</span>`;
  });
  return h + rest.map(c => chp(F.c === c, 'comp', c, '', pres.get(c))).join('');
}
function subRows() {
  const { pres, gs } = groupsInfo();
  return gs.filter(g => openG.has(g.id) && g.codes.length > 1).map(g => `<div class="chips subs"><span class="sl">${E(pres.get(g.codes[0]))}</span>${g.codes.slice(1).map(c => chp(F.c === c, 'comp', c, '', pres.get(c))).join('')}</div>`).join('');
}
function filtHTML() {
  const td = todayK(), tr = tmrK(), base = vis({ t: 1, tm: 1 });
  const nT = base.filter(m => day(m) === td).length, nM = base.filter(m => day(m) === tr).length;
  const nTop = vis({ top: 1 }).filter(isTop).length, nSurp = vis({ surp: 1 }).filter(isSurp).length;
  return chp(F.t, 'ftoday', undefined, 'cal', `Oggi (${nT})`) + chp(F.tm, 'ftomorrow', undefined, 'cal', `Domani (${nM})`) + chp(F.top, 'ftop', undefined, 'zap', `75%+ (${nTop})`) + chp(F.surp, 'fsurp', undefined, 'flame', `Sorprese (${nSurp})`) + chp(F.f, 'ffav', undefined, 'heart', 'Preferiti');
}

function refreshList() {
  $('#hl').innerHTML = listHTML(); const h = $('#hf'); if (h) h.innerHTML = filtHTML();
  $('.sx')?.classList.toggle('hide', !F.q);
}
/* Top 5 marcatori e ammoniti: partite in programma del primo giorno disponibile (di norma oggi) */
function topLists() {
  const up = D.filter(m => m.stato !== 'FINISHED'); if (!up.length) return null;
  const d0 = up.map(day).sort()[0], pool = up.filter(m => day(m) === d0);
  const top = key => { const seen = new Set(); return pool.flatMap(m => pls(m[key]).map(p => ({ name: p.giocatore, team: p.squadra === 'casa' ? m.casa : m.trasf, m, prob: num(p.prob) }))).sort((a, b) => b.prob - a.prob).filter(p => { const k = norm(p.name) + '|' + p.team; if (seen.has(k)) return false; seen.add(k); return true }).slice(0, 5) };
  return { d0, g: top('possibili_marcatori'), y: top('possibili_ammoniti') };
}
function topBox() {
  const t = topLists(); if (!t) return '';
  const row = (p, cl, i) => `<div class="pp ${cl}" data-a="open" data-v="${p.m.id}">${ic(i)}<div class="pn"><b class="tn">${E(p.name)}</b><small class="tn">${E(p.team)} · ${E(p.m.casa)} - ${E(p.m.trasf)}</small></div><div class="pbr"><u style="--w:${p.prob}%"></u></div><span>${p.prob}%</span></div>`;
  const lab = t.d0 === todayK() ? 'Oggi' : t.d0 === tmrK() ? 'Domani' : dlab(t.d0, true);
  return `<details class="acc" id="topd" ${topOpen ? 'open' : ''}><summary>${ic('flame')}Top 5 Marcatori &amp; Ammoniti · ${E(lab)}${ic('chev')}</summary><h4>Più probabili marcatori</h4>${t.g.length ? t.g.map(p => row(p, 'g', 'ball')).join('') : '<p class="mu">Nomi disponibili quando le rose ufficiali sono confermate.</p>'}<h4>Più a rischio cartellino</h4>${t.y.length ? t.y.map(p => row(p, 'y', 'card')).join('') : '<p class="mu">Nomi disponibili quando le rose ufficiali sono confermate.</p>'}</details>`;
}
function vHome() {
  return topSel() + colpo() + topBox() + `<label class="search">${ic('search')}<input id="q" data-s="q" type="search" placeholder="Squadra o giocatore" value="${E(F.q)}" autocomplete="off"><button class="sx ${F.q ? '' : 'hide'}" type="button" data-a="qclear" aria-label="Svuota ricerca">${ic('x')}</button></label>
<div class="chips" id="lc">${leagueChips()}</div><div id="ls">${subRows()}</div><div class="chips" id="hf">${filtHTML()}</div><div id="hl">${listHTML()}</div>` + disc();
}

/* ---------- Live ---------- */
function evIc(e) { const t = norm(e.tipo || e.type || e.t || ''); return /gol|goal/.test(t) ? 'ball' : /esp|ross|red/.test(t) ? 'card' : /amm|giall|yell|card/.test(t) ? 'card' : /sost|sub/.test(t) ? 'sub' : 'ball' }
const liveMin = m => { const v = m.minuto ?? m.minute ?? m.min ?? ''; const t = String(v); return t === '' ? '' : (/^\d+$/.test(t) ? t + "'" : t) };
// "Già centrato" solo per mercati che non possono piu' cambiare con altri gol: Over e Gol
const MONO = /^(O\d\.5|GG)$/;
const hitNow = (esito, score) => !!esito && Array.isArray(score) && String(esito).toUpperCase().replace(/\s+/g, '').split('+').every(t => MONO.test(t)) && evalEsito(esito, score) === true;
function liveBadge(m) {
  const pp = m.pronostico_principale; if (!pp) return '';
  if (m.stato === 'FINISHED') { const ev = esitoOf(m); return ev === null ? '' : `<span class="lst ${ev ? 'ok' : 'ko'}">${ev ? '✓ Centrato' : '✗ Mancato'}</span>` }
  return hitNow(pp.esito, m.score) ? '<span class="lst ok">✓ Già centrato</span>' : (LV(m.stato) ? '<span class="lst run">In corso</span>' : '');
}
function liveCard(m) {
  const lv = LV(m.stato), pp = m.pronostico_principale, alta = pp && num(pp.probabilita) >= 75, mn = liveMin(m), fl = (flash[m.id] || 0) > Date.now(), ev = m.eventi || [];
  return `<article class="card ${fl ? 'goal' : ''}" data-a="open" data-v="${m.id}"><div class="ct"><span class="tn">${E(m.compNome)}</span>${isBig(m) ? '<span class="bm">★ Big Match</span>' : ''}</div><button class="fav ${fav.includes(m.id) ? 'on' : ''}" data-a="fav" data-v="${m.id}" aria-label="Preferita">${ic('heart')}</button>${fl ? `<div class="gfx">${ic('ball')}<b>GOL!</b></div>` : ''}
<div class="mr"><div class="tz">${scudetto(m.casa, m.stemma_casa)}<span class="tn">${E(m.casa)}</span></div><div class="mc">${lv ? `<span class="live"><i></i>LIVE${mn ? ' ' + E(mn) : ''}</span>` : m.stato === 'FINISHED' ? '<span class="mu" style="font-size:11px;font-weight:700">FINALE</span>' : ''}<span class="cdt">${E(dlab(day(m), true))}${lv || !m.score ? '' : ' · ' + tm(m)}</span><b class="tt" style="font-size:24px">${m.score ? m.score.join(' - ') : tm(m)}</b>${alta ? '<span class="hc">Alta confidenza</span>' : ''}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf)}<span class="tn">${E(m.trasf)}</span></div></div>
${pp ? `<div class="lpr"><span class="mu">Pronostico 352</span><span class="bdg" style="--bc:${col(pp.probabilita)}">${E(pp.esito)} · ${num(pp.probabilita)}%</span>${liveBadge(m)}</div>` : ''}
${ev.length ? `<div class="tl">${ev.map(e => `<div>${ic(evIc(e), /esp|ross|red/.test(norm(e.tipo || e.type || '')) ? 'r' : '')}<b>${E(e.minuto ?? e.min ?? '')}'</b> ${E(e.giocatore || e.t || e.testo || '')}</div>`).join('')}</div>` : ''}
<div class="cta">${lbBtn(m)}<span class="cv">Visualizza pronostico${ic('chev')}</span></div></article>`;
}
function vLive() {
  const now = Date.now(), MAX_LIVE_MS = 160 * 60 * 1000;
  const isRealLive = m => {
    if (!LV(m.stato)) return false;
    const t = Date.parse(m.data);
    return !isNaN(t) && (now - t) >= -5 * 60 * 1000 && (now - t) <= MAX_LIVE_MS;
  };
  let l = D.filter(isRealLive).sort((a, b) => a.data.localeCompare(b.data));
  if (liveOnly) l = l.filter(m => m.prob_1x2 || m.pronostico_principale);

  return `<button class="btn" data-a="refresh">${ic('refresh')}Aggiorna Live</button><p class="lcd" id="lcd">Aggiornamento tra ${liveCd}s</p><div class="chips">${chp(!liveOnly, 'lvall', undefined, 'live', 'Tutte le Live')}${chp(liveOnly, 'lvana', undefined, 'chart', 'Solo gare con analisi 352')}</div>` + (l.length ? l.map(liveCard).join('') : `<div class="empty">${ic('live')}</div>`) + disc();
}
// Auto-refresh ogni 50s SOLO con la tab Live aperta e la pagina visibile
function liveTick() { liveCd--; if (liveCd <= 0) { liveCd = 50; refreshLive(false).catch(() => { }) } const e = $('#lcd'); if (e) e.textContent = `Aggiornamento tra ${liveCd}s` }
function liveSync() { const on = tab === 'live' && !document.hidden; if (on && !liveT) { liveCd = 50; liveT = setInterval(liveTick, 1000) } else if (!on && liveT) { clearInterval(liveT); liveT = null } }
async function refreshLive(toastOk) {
  const before = new Map(D.map(m => [m.id, m.score ? m.score.join('-') : '']));
  await loadData(toastOk); liveCd = 50;
  let ch = false;
  D.forEach(m => { if (before.has(m.id) && LV(m.stato) && (m.score ? m.score.join('-') : '') !== before.get(m.id)) { flash[m.id] = Date.now() + 10000; ch = true; setTimeout(() => { if (tab === 'live') render() }, 10100) } });
  if (ch) { tap(880); render() }
}

/* ---------- Generatore + card immagine ---------- */
const comb = () => (out.reduce((a, o) => a * o.v / 100, 1) * 100).toFixed(1);
const gtext = () => '352 Pronostici - Combinazione statistica\n' + out.map((o, i) => `${i + 1}. ${o.m.casa} - ${o.m.trasf}: ${lbl(o.x)} (${o.v}%)`).join('\n') + `\nProbabilità combinata stimata: ${comb()}%\n18+ · Solo informativo e statistico.`;
function genera() {
  const activeGroups = G.best ? Object.keys(GR) : G.m;
  const keys = activeGroups.filter(g => g !== 'MARC').flatMap(g => GR[g] || []);
  const includeMarc = activeGroups.includes('MARC');
  const [lo, hi] = {
    prud: [75, 100],
    bil: [60, 74.9],
    alto: [40, 59.9],
    estr: [18, 44.9],
    all: [0, 100]
  }[G.risk] || [60, 74.9];
  const td = todayK(), tr = tmrK();

  const pool = [];
   D.filter(m => m.stato !== 'FINISHED' && m.prob_1x2 && (G.day === 'all' || (G.day === 'today' && m.data === td) || (G.day === 'tomorrow' && m.data === tr))).forEach(m => {

    const k = mk(m);
    const validi = [];

    keys.forEach(x => {
      const v = +k[x];
      if (v >= lo && v <= hi) validi.push({ x, v });
    });

    if (includeMarc) {
      pls(m.possibili_marcatori).forEach(p => {
        const v = +p.prob;
        if (v >= lo && v <= hi) {
          validi.push({ x: `Segna ${p.giocatore}`, v });
        }
      });
    }

    if (validi.length) {
      const totW = validi.reduce((s, item) => s + Math.max(5, item.v), 0);
      let r = Math.random() * totW, scelto = validi[0];
      for (const item of validi) {
        r -= Math.max(5, item.v);
        if (r <= 0) { scelto = item; break; }
      }
      const peso = (scelto.v / 100) * (0.45 + Math.random() * 1.1);
      pool.push({ m, ...scelto, peso });
    }
  });

  POOL = pool.sort((a, b) => b.peso - a.peso);
  out = POOL.slice(0, G.n);
  cardUrl = '';
  cardBlob = null;
}

const savedHTML = () => {
  const sv = J('saved', []); if (!sv.length) return '';
  return `<div class="box"><h3>${ic('file')}Combinazioni salvate (${sv.length})</h3>` + sv.map((s, i) => {
    const pc = (s.it.reduce((a, o) => a * o.v / 100, 1) * 100).toFixed(1);
    return `<details class="acc" style="margin-bottom:8px"><summary>${ic('target')}<span class="svh tn">${new Date(s.t).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })} · ${s.it.length} eventi<small>${pc}%</small></span>${ic('chev')}</summary>${s.it.map(o => `<div class="sg"><div class="pz">${scudetto(o.c, o.sc, 22)}${scudetto(o.t, o.st, 22)}<span class="tn">${E(o.c)} - ${E(o.t)}</span></div><span class="bdg" style="--bc:${col(o.v)}">${E(lbl(o.x))} · ${o.v}%</span></div>`).join('')}<button class="btn del" data-a="delc" data-v="${i}">${ic('x')}Elimina</button></details>`;
  }).join('') + '</div>';
};
function vGen() {
  const vip = isVip();
  return `<div class="gcount ${vip ? 'vip' : ''}">${vip ? `${ic('gem')}Generazioni illimitate · VIP attivo` : `${ic('zap')}<span>Generazioni rimaste oggi: <b>${genLeft()}/${FREE.gen}</b></span><small>Cambi ↻: ${swapLeft()}/${FREE.swap}</small>`}</div>
<div class="box"><h3>${ic('sliders')}Parametri</h3>
<div class="row"><label>Eventi</label><select data-s="n">${[2, 3, 4, 5, 6, 7, 8].map(n => `<option ${G.n == n ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
<div class="row"><label>Giorno</label>${[['all', 'Tutti i 3 giorni'], ['today', 'Solo Oggi'], ['tomorrow', 'Solo Domani']].map(([v, l]) => `<button class="chip ${G.day === v ? 'on' : ''}" data-a="gday" data-v="${v}">${l}</button>`).join('')}</div>
<div class="row"><button class="chip ${G.best ? 'on' : ''}" data-a="best">${ic('zap')}Mix Completo (Tutti i mercati)</button></div>
<div class="row" style="${G.best ? 'opacity:.4;pointer-events:none' : ''}"><label>Mercati</label>${Object.keys(GR).map(g => `<button class="chip ${G.m.includes(g) ? 'on' : ''}" data-a="mkt" data-v="${g}">${GL[g]}</button>`).join('')}</div>
<div class="row"><label>Livello di rischio</label>${[
      ['prud', 'Prudente >75%'],
      ['bil', 'Bilanciato 60-74%'],
      ['alto', 'Alto Rischio 40-59%'],
      ['estr', 'Estremo <45%'],
      ['all', 'Tutti']
       ].map(([v, l]) => `<button class="chip ${G.risk === v ? 'on' : ''}" data-a="risk" data-v="${v}">${l}</button>`).join('')}</div><button class="btn" data-a="gen">${ic('gen')}Genera Nuova Combinazione</button></div>` +

    (out ? (out.length ? `<div class="box"><h3>${ic('target')}Combinazione statistica</h3>${out.map((o, i) => `
      <div class="sg gs" style="display:block">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <div data-a="open" data-id="${o.m.id}" style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;cursor:pointer">
            ${scudetto(o.m.casa, o.m.stemma_casa, 24)}${scudetto(o.m.trasf, o.m.stemma_trasf, 24)}
            <b style="flex:1;min-width:0;font-size:13.5px;line-height:1.25">${E(o.m.casa)} <span class="mu" style="font-weight:500">vs</span> ${E(o.m.trasf)}</b>
          </div>
          <button class="sw" data-a="swap" data-v="${i}" title="Cambia evento" aria-label="Cambia evento">↻</button>
        </div>
        <div data-a="open" data-id="${o.m.id}" style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;cursor:pointer">
          <span class="mu" style="font-size:11.5px">${E(o.m.competizione || o.m.lega || '')} · ${new Date(o.m.data).toLocaleDateString('it-IT', { weekday: 'short', day: '2-digit', month: 'short' })} ${new Date(o.m.data).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}</span>
          <span class="bdg" style="--bc:${col(o.v)}">${E(lbl(o.x))} · ${o.v}%</span>
        </div>
      </div>`).join('')}<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;margin-top:10px;border-radius:12px;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3)"><span class="mu" style="font-size:12.5px;font-weight:600">Indice combinato stimato</span><b style="font-size:16px;color:var(--ac)">${comb()}%</b></div><button class="btn s" id="cpb" data-a="cp">${ic('copy')}Copia / Condividi</button><button class="btn s" id="savec">${ic('file')}Salva combinazione</button><button class="btn" data-a="mkcard">${ic('img')}Crea Card Immagine</button><div id="cardout">${cardUrl ? cardHTML() : ''}</div></div>` : `<div class="empty">${ic('search')}<p style="font-size:13px;margin-top:6px">Nessun evento trovato con questi filtri. Prova ad ampliare il livello di rischio o i mercati.</p></div>`) : '') + savedHTML() + disc();

}


const cardHTML = () => `<img class="cimg" src="${cardUrl}" alt="Card 352 Pronostici"><button class="btn s" data-a="dl">${ic('down')}Scarica PNG</button><button class="btn s" data-a="shimg">${ic('share')}Condividi immagine</button>`;
async function makeCard() {
  try { await document.fonts?.ready } catch { }
  const n = out.length, W = 1080, H = 400 + n * 150 + 150, cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d'), FN = "'Plus Jakarta Sans',system-ui,sans-serif", FT = "'Outfit','Plus Jakarta Sans',system-ui,sans-serif";
  const rr = (a, b, w, h, r) => { x.beginPath(); x.roundRect ? x.roundRect(a, b, w, h, r) : x.rect(a, b, w, h) };
  const fit = (t, mw) => { while (t.length > 3 && x.measureText(t).width > mw) t = t.slice(0, -2); return t };
  const SH = new Path2D('M3 3h34v21c0 11-8 17-17 20C11 41 3 35 3 24z');
  const cShield = (px, py, w, name, st) => {
    const { c1, c2, p, tc, sig } = sInfo(name, st), s = w / 40; x.save(); x.translate(px, py); x.scale(s, s); x.save(); x.clip(SH); x.fillStyle = c1; x.fillRect(0, 0, 40, 46); x.fillStyle = c2;
    if (p === 'vertical') x.fillRect(14.3, 0, 11.4, 46); else if (p === 'horizontal') x.fillRect(0, 17, 40, 14); else if (p === 'half') x.fillRect(20, 0, 20, 46); else if (p === 'diagonal') { x.beginPath(); x.moveTo(34, -4); x.lineTo(56, -4); x.lineTo(-4, 56); x.lineTo(-4, 34); x.fill() }
    x.restore(); x.lineWidth = 2; x.strokeStyle = p === 'solid' ? c2 : 'rgba(255,255,255,.55)'; x.stroke(SH); x.fillStyle = tc; x.font = `800 13px ${FN}`; x.textAlign = 'center'; x.fillText(sig, 20, 29); x.restore();
  };
  let g = x.createLinearGradient(0, 0, W, H); g.addColorStop(0, '#0B1120'); g.addColorStop(1, '#0f2a3a'); x.fillStyle = g; x.fillRect(0, 0, W, H);
  g = x.createRadialGradient(W * .85, 0, 10, W * .85, 0, 700); g.addColorStop(0, 'rgba(16,185,129,.4)'); g.addColorStop(1, 'rgba(16,185,129,0)'); x.fillStyle = g; x.fillRect(0, 0, W, H);
  g = x.createLinearGradient(60, 60, 140, 160); g.addColorStop(0, '#10B981'); g.addColorStop(1, '#06B6D4'); x.save(); x.translate(60, 70); x.scale(2.2, 2.4); x.fillStyle = g; x.fill(SH); x.restore();
  x.textAlign = 'left'; x.fillStyle = '#fff'; x.font = `800 60px ${FT}`; x.fillText('352 Pronostici', 180, 122); x.fillStyle = '#8A97AD'; x.font = `600 30px ${FN}`; x.fillText('Combinazione statistica · ' + new Date().toLocaleDateString('it-IT', { day: 'numeric', month: 'long' }), 180, 170);
  out.forEach((o, i) => {
    const y = 250 + i * 150, v = o.v; x.fillStyle = 'rgba(255,255,255,.07)'; rr(50, y, 980, 130, 28); x.fill(); x.strokeStyle = 'rgba(255,255,255,.1)'; x.lineWidth = 2; x.stroke();
    cShield(75, y + 22, 62, o.m.casa, o.m.stemma_casa); cShield(150, y + 22, 62, o.m.trasf, o.m.stemma_trasf);
    x.textAlign = 'left'; x.fillStyle = '#fff'; x.font = `800 34px ${FN}`; x.fillText(fit(`${o.m.casa} - ${o.m.trasf}`, 540), 240, y + 56); x.fillStyle = '#8A97AD'; x.font = `600 28px ${FN}`; x.fillText(lbl(o.x), 240, y + 92);
    x.fillStyle = 'rgba(255,255,255,.12)'; rr(240, y + 106, 540, 9, 5); x.fill(); x.fillStyle = col(v); rr(240, y + 106, 540 * v / 100, 9, 5); x.fill();
    x.textAlign = 'right'; x.fillStyle = col(v); x.font = `800 64px ${FN}`; x.fillText(v + '%', 1000, y + 82);
  });
  const fy = 250 + n * 150 + 30; x.textAlign = 'left'; x.fillStyle = '#FBBF24'; x.font = `800 40px ${FN}`; x.fillText(`Probabilità combinata stimata: ${comb()}%`, 60, fy + 40); x.fillStyle = '#8A97AD'; x.font = `600 26px ${FN}`; x.fillText('18+ · Contenuto solo informativo e statistico', 60, fy + 92);
  /* Branding 352 Pronostici in basso */
  x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 2; x.beginPath(); x.moveTo(60, H - 150); x.lineTo(W - 60, H - 150); x.stroke();
  x.save(); x.translate(60, H - 128); x.scale(1.6, 1.75); g = x.createLinearGradient(0, 0, 40, 46); g.addColorStop(0, '#10B981'); g.addColorStop(1, '#06B6D4'); x.fillStyle = g; x.fill(SH); x.restore();
  g = x.createLinearGradient(150, 0, 470, 0); g.addColorStop(0, '#10B981'); g.addColorStop(1, '#06B6D4'); x.textAlign = 'left'; x.fillStyle = g; x.font = `800 50px ${FT}`; x.fillText('352 Pronostici', 150, H - 80);
  x.fillStyle = '#8A97AD'; x.font = `600 26px ${FN}`; x.fillText('Analisi & Statistiche Calcio', 150, H - 40);
  return new Promise(r => cv.toBlob(b => r(b), 'image/png'));
}

/* ---------- Info ---------- */
function vInfo() {
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone, hs = histStats(), dark = document.documentElement.dataset.theme === 'dark';
  return `<div class="ig"><div class="ib2">${ic('chart')}Probabilità e affidabilità</div><div class="ib2">${ic('users')}Rose ufficiali aggiornate</div><div class="ib2">${ic('shield')}Nessun dato personale</div><div class="ib2"><div class="age" style="width:34px;height:34px;font-size:12px;margin:0 auto 8px">18+</div>Solo maggiorenni</div></div>
<div class="box"><h3>${ic('sliders')}Impostazioni</h3><div class="row2"><button class="btn s" data-a="theme">${ic(dark ? 'sun' : 'moon')}Tema ${dark ? 'chiaro' : 'scuro'}</button><button class="btn s" data-a="share">${ic('share')}Condividi app</button></div></div>
<div class="box"><h3>${ic('check')}Statistiche verificate</h3>${hs.y ? `<p style="font-size:14px;font-weight:700">Statistiche verificate: ${hs.x}/${hs.y} (${hs.p}%)</p><div class="sbar" style="--w:${hs.p}%"><u></u></div><p class="mu" style="font-size:12px;margin-top:8px">Confronto automatico tra il pronostico principale e il risultato finale delle partite concluse.</p>` : `<p class="mu" style="font-size:13px">Appariranno qui non appena ci saranno partite concluse con un pronostico verificabile.</p>`}</div>
<div class="box"><h3>${ic('info')}Come leggere i dati</h3><p class="mu" style="font-size:13px">Un modello AI stima le probabilità usando forma, classifica e rose. Sono stime statistiche, non certezze. Nessuna quota, nessun invito al gioco; gli scudetti sono generati dai colori sociali.</p></div>
${standalone ? '' : `<button class="btn" data-a="install">${ic('down')}Installa App</button>`}` + disc();
}

/* ---------- Centrate / Braccio di Ferro ---------- */
const WIN_PRESETS = [
  { k: 'w8', n: 8, t: '⚡ Generatore 352 · Combinazione 8/8', tag: 'CENTRATA' },
  { k: 'w10', n: 10, t: '👑 Selezione VIP · Combinazione 10/10', tag: 'VIP 100%' },
  { k: 'w15', n: 15, t: '🔥 Modello AI 352 · Combinazione 15/15', tag: 'RECORD' }
];
function winCards() {
  const hits = D.filter(m => esitoOf(m) === true).sort((a, b) => b.data.localeCompare(a.data));
  const list = WIN_PRESETS.filter(p => hits.length >= p.n).map((p, idx) => ({
    ...p,
    rows: hits.slice(idx * 2, idx * 2 + p.n).length === p.n ? hits.slice(idx * 2, idx * 2 + p.n) : hits.slice(0, p.n)
  }));
  return { hits: hits.length, list };
}
const ticks = n => `<div class="wtk">${'<span class="tk">✓</span>'.repeat(n)}</div>`;
function winText(c) {
  return `352 Pronostici - ${c.t}\n` + c.rows.map(m => `✓ ${m.casa} - ${m.trasf}: ${m.pronostico_principale.esito}${m.score ? ' (' + m.score.join('-') + ')' : ''}`).join('\n') + '\n18+ · Solo informativo e statistico.';
}
function vWin() {
  const w = winCards(), l = w.list.filter(c => winF === 'all' || c.n === +winF);
  const chips = [['all', 'Tutte'], ['8', '8 Eventi'], ['10', '10 Eventi'], ['15', '15 Eventi']].map(([v, t]) => `<button class="chip ${winF === v ? 'on' : ''}" data-a="wf" data-v="${v}">${t}</button>`).join('');
  return `<div class="chips">${chips}</div>
<p class="mu" style="font-size:12px;margin:0 2px 10px">Esiti principali 352 centrati verificati: <b style="color:var(--tx)">${w.hits}</b></p>`
    + (l.length ? l.map(c => `<article class="wc real"><div class="wh"><span class="wt tn">${ic('trophy')}${E(c.t)}</span><span class="wbd ok">${E(c.tag)}</span></div>
${ticks(c.n)}
${c.rows.map(m => `<div class="wr"><span class="tk s">✓</span><div class="pz">${scudetto(m.casa, m.stemma_casa, 22)}${scudetto(m.trasf, m.stemma_trasf, 22)}<span class="tn">${E(m.casa)} - ${E(m.trasf)}</span></div><span class="bdg" style="--bc:${col(m.pronostico_principale.probabilita)}">${E(m.pronostico_principale.esito)}</span><b class="sc2">${m.score ? m.score.join('-') : ''}</b></div>`).join('')}
<button class="btn s" data-a="wshare" data-v="${c.k}">${ic('share')}Condividi risultato</button></article>`).join('') : `<div class="empty">${ic('arm')}<b style="display:block;color:var(--tx);font-family:var(--fh)">Nessuna combinazione da ${winF} eventi ancora</b><p style="font-size:13px;margin-top:4px">Le combinazioni appaiono automaticamente man mano che le partite concluse vengono centrate.</p></div>`) + disc();
}


/* ---------- Zona VIP ---------- */
// Link Revolut con importo e causale precompilati (REVOLUT_CENTS: importo in centesimi)
const payUrl = p => `${VIP_PAY_URL}?amount=${REVOLUT_CENTS ? Math.round(p.amount * 100) : p.amount.toFixed(2)}&currency=EUR&note=${encodeURIComponent(p.cause)}`;
function vVip() {
  const act = isVip(), adm = isAdmin(), sel = VIP_PLANS.find(p => p.days === vipSel);
  const status = adm ? `<div class="vstat">${ic('gem')}<div><b>ADMIN CREATORE · ACCESSO ILLIMITATO</b><small>Accesso VIP permanente, senza scadenza</small></div></div><button class="btn ${simStd ? 'gold' : ''}" data-a="simstd">${simStd ? 'Torna Admin' : 'Simula vista Standard'}</button>${simStd ? '<p class="mu" style="font-size:12px;text-align:center;margin:8px 0 0">Stai vedendo l’app come utente Standard (limiti e blocchi attivi).</p>' : ''}<button class="btn s" data-a="adminoff">Disattiva accesso Admin su questo dispositivo</button><div style="height:12px"></div>` : act ? `<div class="vstat">${ic('clock')}<div><b>Pass VIP attivo · ${E(vipLeft())} rimasti</b><small>Scade il ${new Date(+L.vipExp).toLocaleString('it-IT', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</small></div></div>` : '';
  return `<section class="vip-page">
<div class="vh">${ic('gem', 'gem')}<h1>352 VIP Club</h1><p>Analisi senza limiti, zero pubblicità, premi esclusivi</p></div>
${status}
<div class="vbox"><h3>${ic('gem')}Tutti i vantaggi inclusi</h3><ul class="vl">
<li>${ic('inf')}<span><b>Pronostici e analisi AI illimitati</b> ogni giorno</span></li>
<li>${ic('gen')}<span><b>Generatore statistico senza limiti</b> + cambio singolo evento ↻ + salvataggio delle combinazioni</span></li>
<li>${ic('block')}<span><b>Navigazione 100% senza pubblicità</b></span></li>
<li>${ic('gift')}<span><b>Accesso ai Contest &amp; Premi Esclusivi del Club</b>: iniziative periodiche riservate ai membri VIP con in palio maglie ufficiali da calcio, scarpini, cappelli e merchandising sportivo</span></li>
</ul>
<p class="vnote">Contest riservati ai membri con Pass VIP attivo. Date, modalità di partecipazione e premi di ogni iniziativa sono indicati nel relativo regolamento, pubblicato prima dell'avvio e comunicato agli iscritti via email. I premi sono articoli sportivi in natura.</p></div>
<h2 class="vt">Scegli il tuo Pass</h2>
${VIP_PLANS.map(p => `<div class="plan ${p.tag ? 'hl' : ''} ${vipSel === p.days ? 'sel' : ''}">${p.tag ? `<span class="ptag">${E(p.tag)}</span>` : ''}<div class="pn2"><b>${E(p.name)}</b><small>${E(p.note)}</small></div><div class="pr2">${E(p.price)}</div><div class="psub">${E(p.sub)}</div><button class="gbtn" type="button" data-a="vipsel" data-v="${p.days}">${ic('gem')}Scegli ${E(p.name.replace('Pass ', ''))} · ${E(p.price)}</button></div>`).join('')}
<div class="vbox vsum" id="vsum">
  <h3>${ic('gem')}Lista d'Attesa VIP (Posti Esauriti)</h3>
  <p class="vnote" style="border:0;padding:0 0 10px 0;color:#cbd5e1;">
    Per garantire la massima qualità delle analisi, gli accessi VIP di questo mese sono al completo. Lascia la tua email per prenotare un posto e ricevere il <b>20% di sconto</b> appena riaprono le iscrizioni:
  </p>
  <div id="vwait-box" style="display:flex;flex-direction:column;gap:10px;margin-top:8px;">
    <select id="vwait-plan" style="padding:12px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#fff;width:100%;box-sizing:border-box;">
      <option value="Pass Mensile (14,99 €)" selected>Piano preferito: Pass Mensile (14,99 €)</option>
      <option value="Pass Settimanale (4,99 €)">Piano preferito: Pass Settimanale (4,99 €)</option>
      <option value="Pass Annuale (49,99 €)">Piano preferito: Pass Annuale (49,99 €)</option>
    </select>
    <input type="email" id="vwait-email" placeholder="Inserisci la tua email..." style="padding:12px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#fff;width:100%;box-sizing:border-box;">
    <label style="font-size:11px;color:#94a3b8;text-align:left;display:flex;align-items:flex-start;gap:6px;">
      <input type="checkbox" id="vwait-chk" style="margin-top:2px;">
      <span>Acconsento a ricevere una singola email di avviso alla riapertura dei posti VIP (nessuno spam).</span>
    </label>
    <button type="button" id="vwait-btn" onclick="const e=document.getElementById('vwait-email').value.trim(), c=document.getElementById('vwait-chk').checked, p=document.getElementById('vwait-plan').value, b=this; if(!e||!e.includes('@')){alert('Inserisci una email valida');return;} if(!c){alert('Spunta la casella del consenso');return;} b.disabled=true; b.innerText='Invio in corso...'; fetch('https://web3forms.com',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({access_key:'e4694674-17f8-4eb9-ab0b-d29430ae98d3',subject:'Nuovo iscritto Lista d Attesa 352 VIP!',email:e,piano_interessato:p})}).then(r=>r.json()).then(res=>{if(res.success){document.getElementById('vwait-box').style.display='none';document.getElementById('vwait-ok').style.display='block';}else{b.disabled=false;b.innerText='Errore: '+(res.message||'riprova');}}).catch(()=>{b.disabled=false;b.innerText='Errore di connessione';});" class="gbtn" style="border:none;cursor:pointer;width:100%;justify-content:center;">${ic('gem')}Avvisami quando riapre 🚀</button>
  </div>
  <p id="vwait-ok" style="display:none;color:#4ade80;font-weight:bold;font-size:14px;margin-top:10px;">✅ Sei in lista! Ti avviseremo appena si libera un posto.</p>
</div>

<div class="vbox"><h3>${ic('key')}Attiva il tuo Codice Pass VIP</h3>
<div class="vin"><input id="vcode" type="text" placeholder="Es. M30-XXXX-XXXX" autocomplete="off" autocapitalize="characters" spellcheck="false"><button class="gbtn" type="button" data-a="vipact">Attiva Pass VIP</button></div>
${act ? `<p class="vnote" style="border:0;padding-top:6px">Se inserisci un nuovo codice, i giorni si sommano al tuo Pass attuale.</p>` : ''}</div>
${disc()}</section>`;
}

/* ---------- Scheda partita ---------- */
const pollBox = m => { const v = J('poll', {})[m.id], p = m.prob_1x2 || {}; return `<h3>${ic('users')}Sondaggio rapido</h3><div class="pollb">${['1', 'X', '2'].map(x => `<button class="pv ${v === x ? 'on' : ''}" data-a="vote" data-v="${m.id}|${x}">${x}</button>`).join('')}</div>${v ? ['1', 'X', '2'].map(x => `<div class="cmp"><b>${x}</b><div class="cb"><u style="width:${num(p[x])}%;background:#06B6D4"></u>${v === x ? '<s class="you">TU</s>' : ''}</div><span>AI ${num(p[x])}%</span></div>`).join('') : ''}` };
function sheet(m) {
  storyUrl = ''; storyBlob = null;
  const pp = m.pronostico_principale, k = mk(m), mc = m.mercati_completi || {}, pl = (arr, cl, i) => pls(arr).map(p => `<div class="pp ${cl}">${ic(i)}<div class="pn"><b class="tn">${E(p.giocatore)}</b><small class="tn">${E(p.squadra === 'casa' ? m.casa : m.trasf)}</small></div><div class="pbr"><u style="--w:${num(p.prob)}%"></u></div><span>${num(p.prob)}%</span></div>`).join('');
  const ig = Math.round(((+k['O2.5'] || 0) + (+k.GG || 0)) / 2), ev = esitoOf(m);
  $('#sbody').innerHTML = `<div class="sh2"><div class="tz">${scudetto(m.casa, m.stemma_casa, 52)}<span class="tn">${E(m.casa)}</span></div><div class="sc">${m.score ? m.score.join(' - ') : tm(m)}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf, 52)}<span class="tn">${E(m.trasf)}</span></div></div>
<p class="mu" style="text-align:center;font-size:12px">${E(m.compNome)} · ${dlab(day(m))}${isBig(m) ? ' · <span class="bm" style="margin-left:4px">★ Big Match</span>' : ''}</p>
${lbBtn(m, 'big')}
${ev !== null ? `<p class="evl ${ev ? 'ok' : 'ko'}" style="margin-top:10px">${ev ? '✓ Pronostico centrato' : '✗ Pronostico mancato'}</p>` : ''}
${pp ? `<div class="hero">${ring(pp.probabilita, 96, 11)}<div class="hi"><small>${ic('target')}PRONOSTICO CONSIGLIATO</small><div class="hx tn">${E(String(pp.esito).toUpperCase())}</div>${num(pp.probabilita) >= 75 ? '<span class="hc">Alta confidenza</span><br>' : ''}${pp.motivazione_breve ? `<span class="mp">${E(clean(pp.motivazione_breve))}</span>` : ''}</div></div>` : ''}
${m.prob_1x2 ? `<div class="box"><h3>${ic('chart')}Affidabilità e Indice Gol</h3><div class="gg">${gauge(m.affidabilita)}<div><div class="pl"><span>${ic('flame', '')}Indice Gol ${num(ig)}</span></div><div class="pt"><b style="--w:${num(ig)}%;background:${col(ig)}"></b></div></div></div></div>
<div class="box"><h3>${ic('live')}Probabilità</h3>${bar([{ l: '1', v: k['1'], c: '#10B981' }, { l: 'X', v: k.X, c: '#64748B' }, { l: '2', v: k['2'], c: '#06B6D4' }])}${bar([{ l: 'Gol', v: k.GG, c: '#10B981' }, { l: 'NoGol', v: k.NG, c: '#EF4444' }])}${bar([{ l: 'Under 2.5', v: k['U2.5'], c: '#8B5CF6' }, { l: 'Over 2.5', v: k['O2.5'], c: '#F59E0B' }])}</div>
${forze(m)}
    <div class="box"><h3>${ic('sliders')}Mercati e Combo</h3><div class="tiles">${Object.entries(mc).map(([x, v]) => `<div class="tile ${num(v) >= 75 ? 'hi' : ''}"><small>${E(lbl(x))}</small><b>${num(v)}%</b></div>`).join('')}</div>${['DNB', 'SQ', 'TM'].map(g => `<details class="acc" style="margin-top:8px"><summary>${E(GL[g])}${ic('chev')}</summary><div class="tiles" style="margin-top:8px">${(GR[g] || []).filter(x => k[x] != null).map(x => `<div class="tile ${num(k[x]) >= 75 ? 'hi' : ''}"><small>${E(lbl(x))}</small><b>${num(k[x])}%</b></div>`).join('')}</div></details>`).join('')}</div>

${pitch(m) ? `<div class="box"><h3>${ic('users')}Probabili formazioni</h3>${pitch(m)}</div>` : ''}
<div class="box"><h3>${ic('ball')}Probabili marcatori</h3>${pl(m.possibili_marcatori, 'g', 'ball') || '<p class="mu">–</p>'}</div>
<div class="box"><h3>${ic('card')}Rischio cartellino</h3>${pl(m.possibili_ammoniti, 'y', 'card') || '<p class="mu">–</p>'}</div>
${isVip() ? '' : '<div class="ad-sheet" id="ad-sheet-bottom"></div>'}
<div class="box" id="poll">${pollBox(m)}</div>
<div class="box"><h3>${ic('img')}Condividi la partita</h3><button class="btn" data-a="mkstory" data-v="${m.id}">${ic('img')}Crea Card Partita (Storie 9:16)</button><div id="stout"></div></div>
<details class="acc"><summary>${ic('file')}Dettagli testuali AI${ic('chev')}</summary><p>${E(clean(m.analisi))}</p></details>` : `<div class="empty">${ic('search')}</div>`}${disc()}`;
  $('#sheet').dataset.id = m.id; $('#sheet').scrollTop = 0; $('#sheet').classList.add('open'); $('#scrim').classList.add('open');
}

/* ---------- Casa vs Trasferta + Card Storie 9:16 ---------- */
const vsBar = (l, a, b) => `<div class="vs"><div class="vl2"><b>${num(a)}</b><span>${l}</span><b>${num(b)}</b></div><div class="vt2"><i style="flex:${num(a) || 1};background:#10B981"></i><i style="flex:${num(b) || 1};background:#06B6D4"></i></div></div>`;
function forze(m) {
  const k = mk(m), x = +k.X || 0, fc = Math.round((+k['1'] || 0) + x / 2), ft = Math.round((+k['2'] || 0) + x / 2), ig = ((+k['O2.5'] || 0) + (+k.GG || 0)) / 2, oc = Math.round(ig * .4 + fc * .6), ot = Math.round(ig * .4 + ft * .6);
  return `<div class="box"><h3>${ic('target')}Casa vs Trasferta</h3><div class="vn"><span class="tn">${E(m.casa)}</span><span class="tn">${E(m.trasf)}</span></div>${vsBar('Indice di Forza', fc, ft)}${vsBar('Potenziale Offensivo', oc, ot)}<p class="mu" style="font-size:11px">Indici statistici derivati dalle probabilità del modello.</p></div>`;
}
const storyHTML = () => `<img class="cimg" src="${storyUrl}" alt="Card partita 352 Pronostici"><button class="btn s" data-a="dlstory">${ic('down')}Scarica PNG</button><button class="btn s" data-a="shstory">${ic('share')}Condividi immagine</button>`;
async function makeStory(m) {
  try { await document.fonts?.ready } catch { }
  const W = 1080, H = 1920, cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  const x = cv.getContext('2d'), FN = "'Plus Jakarta Sans',system-ui,sans-serif", FT = "'Outfit','Plus Jakarta Sans',system-ui,sans-serif", SH = new Path2D('M3 3h34v21c0 11-8 17-17 20C11 41 3 35 3 24z');
  const rr = (a, b, w, h, r) => { x.beginPath(); x.roundRect ? x.roundRect(a, b, w, h, r) : x.rect(a, b, w, h) };
  const fit = (t, mw) => { t = String(t); while (t.length > 3 && x.measureText(t).width > mw) t = t.slice(0, -2); return t };
  const shield = (px, py, w, name, st) => {
    const { c1, c2, p, tc, sig } = sInfo(name, st), s = w / 40; x.save(); x.translate(px, py); x.scale(s, s); x.save(); x.clip(SH); x.fillStyle = c1; x.fillRect(0, 0, 40, 46); x.fillStyle = c2;
    if (p === 'vertical') x.fillRect(14.3, 0, 11.4, 46); else if (p === 'horizontal') x.fillRect(0, 17, 40, 14); else if (p === 'half') x.fillRect(20, 0, 20, 46); else if (p === 'diagonal') { x.beginPath(); x.moveTo(34, -4); x.lineTo(56, -4); x.lineTo(-4, 56); x.lineTo(-4, 34); x.fill() }
    x.restore(); x.lineWidth = 2; x.strokeStyle = p === 'solid' ? c2 : 'rgba(255,255,255,.55)'; x.stroke(SH); x.fillStyle = tc; x.font = `800 13px ${FN}`; x.textAlign = 'center'; x.fillText(sig, 20, 29); x.restore();
  };
  const k = mk(m), pp = m.pronostico_principale;
  let main = pp ? { x: String(pp.esito), v: num(pp.probabilita) } : null;
  const all = Object.entries(k).map(([a, v]) => ({ x: a, v: Math.round(+v) })).filter(o => o.v > 0).sort((a, b) => b.v - a.v);
  if (!main && all[0]) main = all[0];
  let g = x.createLinearGradient(0, 0, W, H); g.addColorStop(0, '#0B1120'); g.addColorStop(1, '#0f2a3a'); x.fillStyle = g; x.fillRect(0, 0, W, H);
  g = x.createRadialGradient(W * .8, 200, 10, W * .8, 200, 900); g.addColorStop(0, 'rgba(16,185,129,.35)'); g.addColorStop(1, 'rgba(16,185,129,0)'); x.fillStyle = g; x.fillRect(0, 0, W, H);
  for (let i = 0; i < 8; i++) { x.fillStyle = i % 2 ? 'rgba(16,185,129,.05)' : 'rgba(16,185,129,.02)'; x.fillRect(0, 760 + i * 145, W, 145) }
  /* logo */
  g = x.createLinearGradient(60, 70, 120, 140); g.addColorStop(0, '#10B981'); g.addColorStop(1, '#06B6D4'); x.save(); x.translate(60, 70); x.scale(1.7, 1.9); x.fillStyle = g; x.fill(SH); x.restore();
  x.textAlign = 'left'; x.fillStyle = '#fff'; x.font = `800 52px ${FT}`; x.fillText('352 Pronostici', 150, 128);
  /* porta con rete */
  const gx = 120, gy = 210, gw = 840, gh = 380;
  x.save(); x.beginPath(); x.rect(gx, gy, gw, gh); x.clip(); x.fillStyle = 'rgba(255,255,255,.04)'; x.fillRect(gx, gy, gw, gh); x.strokeStyle = 'rgba(255,255,255,.17)'; x.lineWidth = 2;
  for (let i = gx; i <= gx + gw; i += 32) { x.beginPath(); x.moveTo(i, gy); x.lineTo(i, gy + gh); x.stroke() }
  for (let j = gy; j <= gy + gh; j += 32) { x.beginPath(); x.moveTo(gx, j); x.lineTo(gx + gw, j); x.stroke() }
  x.restore();
  x.strokeStyle = '#fff'; x.lineWidth = 14; x.lineCap = 'round'; x.lineJoin = 'round'; x.beginPath(); x.moveTo(gx, gy + gh); x.lineTo(gx, gy); x.lineTo(gx + gw, gy); x.lineTo(gx + gw, gy + gh); x.stroke();
  x.strokeStyle = 'rgba(255,255,255,.35)'; x.lineWidth = 4; x.beginPath(); x.moveTo(60, gy + gh + 8); x.lineTo(W - 60, gy + gh + 8); x.stroke();
  shield(gx + 120, gy + 70, 200, m.casa, m.stemma_casa); shield(gx + gw - 320, gy + 70, 200, m.trasf, m.stemma_trasf);
  x.textAlign = 'center'; x.fillStyle = '#8A97AD'; x.font = `800 56px ${FT}`; x.fillText('VS', W / 2, gy + 215);
  x.fillStyle = '#fff'; x.font = `800 40px ${FN}`; x.fillText(fit(m.casa, 440), gx + 220, gy + gh + 80); x.fillText(fit(m.trasf, 440), gx + gw - 220, gy + gh + 80);
  x.fillStyle = '#8A97AD'; x.font = `600 30px ${FN}`; x.fillText(fit(`${m.compNome} · ${dlab(day(m))} · ${tm(m)}`, 940), W / 2, gy + gh + 140);
  /* pronostico */
  if (main) {
    x.fillStyle = 'rgba(255,255,255,.07)'; rr(60, 840, 960, 300, 36); x.fill(); x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 2; x.stroke();
    x.textAlign = 'left'; x.fillStyle = '#8A97AD'; x.font = `700 28px ${FN}`; x.fillText('PRONOSTICO CONSIGLIATO', 100, 900);
    x.fillStyle = '#fff'; x.font = `800 104px ${FT}`; x.fillText(fit(main.x.toUpperCase(), 520), 100, 1020);
    x.textAlign = 'right'; x.fillStyle = col(main.v); x.font = `800 104px ${FT}`; x.fillText(main.v + '%', 980, 1020);
    x.fillStyle = 'rgba(255,255,255,.12)'; rr(100, 1055, 880, 14, 7); x.fill(); x.fillStyle = col(main.v); rr(100, 1055, 880 * main.v / 100, 14, 7); x.fill();
    x.textAlign = 'left'; x.fillStyle = '#8A97AD'; x.font = `600 28px ${FN}`; x.fillText(m.affidabilita != null ? `Affidabilità ${num(m.affidabilita)}%` : 'Stima statistica', 100, 1112);
  }
  /* altri mercati */
  const others = all.filter(o => !main || o.x !== main.x).slice(0, 4);
  x.textAlign = 'left'; x.fillStyle = '#fff'; x.font = `800 36px ${FT}`; x.fillText('Altri mercati', 70, 1210);
  others.forEach((o, i) => {
    const y = 1240 + i * 100; x.fillStyle = 'rgba(255,255,255,.06)'; rr(60, y, 960, 84, 24); x.fill();
    x.textAlign = 'left'; x.fillStyle = '#fff'; x.font = `700 30px ${FN}`; x.fillText(fit(lbl(o.x), 520), 90, y + 53);
    x.fillStyle = 'rgba(255,255,255,.12)'; rr(560, y + 36, 300, 10, 5); x.fill(); x.fillStyle = col(o.v); rr(560, y + 36, 300 * o.v / 100, 10, 5); x.fill();
    x.textAlign = 'right'; x.fillStyle = col(o.v); x.font = `800 34px ${FN}`; x.fillText(o.v + '%', 996, y + 54);
  });
  /* branding */
  x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 2; x.beginPath(); x.moveTo(60, 1680); x.lineTo(W - 60, 1680); x.stroke();
  x.save(); x.translate(60, 1710); x.scale(1.5, 1.7); g = x.createLinearGradient(0, 0, 40, 46); g.addColorStop(0, '#10B981'); g.addColorStop(1, '#06B6D4'); x.fillStyle = g; x.fill(SH); x.restore();
  g = x.createLinearGradient(150, 0, 470, 0); g.addColorStop(0, '#10B981'); g.addColorStop(1, '#06B6D4'); x.textAlign = 'left'; x.fillStyle = g; x.font = `800 48px ${FT}`; x.fillText('352 Pronostici', 150, 1758);
  x.fillStyle = '#8A97AD'; x.font = `600 24px ${FN}`; x.fillText('Analisi & Statistiche Calcio', 150, 1796);
  x.font = `600 22px ${FN}`; x.fillText('18+ · Contenuto solo informativo e statistico', 60, 1862);
  return new Promise(r => cv.toBlob(b => r(b), 'image/png'));
}

/* ---------- Pannello Campanellina ---------- */
function npHTML() {
  const an = D.filter(m => m.prob_1x2), td = todayK(), tr = tmrK(), nT = an.filter(m => day(m) === td).length, nM = an.filter(m => day(m) === tr).length, nTop = an.filter(m => m.stato !== 'FINISHED' && isTop(m)).length, nL = D.filter(m => LV(m.stato)).length;
  const vip = isVip(), st = isAdmin() && !simStd ? 'Admin Creatore · accesso permanente' : vip ? `Pass VIP attivo · ${vipLeft()} rimasti` : `Piano Standard · ${FREE.matches} pronostici e ${FREE.gen} generazioni al giorno`;
  return `<div class="mb np"><button class="ib vx" data-a="npclose" aria-label="Chiudi">${ic('x')}</button><h2>${ic('bell')} Notifiche</h2>
<div class="box"><h3>${ic('chart')}Gare analizzate (3 giorni)</h3><div class="npr"><span>Totale</span><b>${an.length}</b></div><div class="npr"><span>Oggi</span><b>${nT}</b></div><div class="npr"><span>Domani</span><b>${nM}</b></div><div class="npr"><span>Selezioni 80%+ in programma</span><b>${nTop}</b></div><div class="npr"><span>Live in corso</span><b>${nL}</b></div></div>
<div class="box npg"><h3>${ic('gift')}Contest VIP del mese</h3><p>In palio per i membri VIP: <b>maglie ufficiali da calcio, scarpini e cappelli</b>. Date, modalità di partecipazione e regolamento saranno pubblicati prima dell’avvio e comunicati via email agli iscritti. Premi in natura, riservato ai Pass VIP attivi.</p>${vip ? '' : `<button class="btn gold" data-a="vipgo">Scopri il Club VIP 💎</button>`}</div>
<div class="box"><h3>${ic('gem')}Il tuo piano</h3><p class="mu" style="font-size:13px">${E(st)}</p></div>
<div class="box"><div class="npr"><span><b style="color:var(--tx)">Suoni e vibrazione</b><br><small class="mu">Feedback quando tocchi l’app</small></span><button class="swt ${fx() ? 'on' : ''}" role="switch" aria-checked="${fx()}" aria-label="Suoni e vibrazione" data-a="fxtog"><i></i></button></div></div></div>`;
}
function openNP() {
  let e = $('#np'); if (!e) { e = document.createElement('div'); e.id = 'np'; e.className = 'modal'; e.setAttribute('role', 'dialog'); e.setAttribute('aria-modal', 'true'); e.setAttribute('aria-label', 'Notifiche'); document.body.appendChild(e) }
  e.innerHTML = npHTML(); e.classList.add('open');
}

/* ---------- Render e stato ---------- */
// Badge: contatore Lista (nav) e stato VIP (header)
function stats() {
  const n = J('lst', []).length, b = $('#lstb'); if (b) { b.textContent = n > 99 ? '99+' : n; b.classList.toggle('hide', !n) }
}
function render() {
  const vip = isVip(); document.documentElement.dataset.vip = vip ? '1' : '0';
  $('#view').innerHTML = { home: vHome, live: vLive, gen: vGen, list: vList, vip: vVip, win: vWin, info: vInfo }[tab]();
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('on', b.dataset.v === tab));
  $('#hb').innerHTML = vip ? `<button class="vbadge on" data-a="tab" data-v="vip">${ic('gem')}VIP ATTIVO</button>` : `<button class="vbadge" data-a="tab" data-v="vip">Passa a VIP 💎</button>`;
  stats(); liveSync();
}
const skeleton = () => '<div class="skc"><div class="sk1"></div><div class="skr"><i class="sk2"></i><i class="sk3"></i><i class="sk2"></i></div><div class="sk4"></div></div>'.repeat(4);
async function loadData(toastOk) {
  const r = await fetch('data/matches.json?t=' + Date.now(), { cache: 'no-store' }); const j = await r.json();
  D = j.matches || []; meta = j.aggiornato_il || j.aggiornato || j.updated_at || ''; histSync(); render(); if (toastOk) toast('Dati aggiornati');
}

/* ---------- Installa app ---------- */
let dip = null; const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone, IOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
const instUI = () => $('#inst')?.classList.toggle('hide', standalone() || !(dip || IOS));
addEventListener('beforeinstallprompt', e => { e.preventDefault(); dip = e; instUI() });
addEventListener('appinstalled', () => { dip = null; instUI() });

/* ---------- Azioni ---------- */
const A = {
  tab(v) { tap(520); tab = v; render(); scrollTo(0, 0) },
  comp(v) { F.c = v; render() }, favf() { F.f = !F.f; render() },
  gtog(v) { tap(600); openG.has(v) ? openG.delete(v) : openG.add(v); const a = $('#lc'), b = $('#ls'); if (a && b) { a.innerHTML = leagueChips(); b.innerHTML = subRows() } else render() },
  ftoday() { F.t = !F.t; if (F.t) F.tm = false; render() },
  ftomorrow() { F.tm = !F.tm; if (F.tm) F.t = false; render() },
  ftop() { F.top = !F.top; render() },
  qclear() { F.q = ''; const i = $('#q'); if (i) i.value = ''; refreshList(); tap(600) },
  open(v) { const m = D.find(x => x.id == v); if (m && gateMatch(m)) { tap(); sheet(m) } },
  close() { $('#sheet').classList.remove('open'); $('#scrim').classList.remove('open') },
  fav(v) { v = +v; tap(880); fav = fav.includes(v) ? fav.filter(x => x != v) : [...fav, v]; L.fav = JSON.stringify(fav); if (F.f) return render(); document.querySelectorAll(`[data-a=fav][data-v="${v}"]`).forEach(b => b.classList.toggle('on', fav.includes(v))); stats() },
  /* La Mia Lista */
  lst(v) {
    v = +v; let l = J('lst', []); const was = l.includes(v);
    l = was ? l.filter(x => x != v) : [...l, v]; L.lst = JSON.stringify(l); tap(was ? 500 : 820);
    document.querySelectorAll(`[data-a=lst][data-v="${v}"]`).forEach(b => { b.classList.toggle('on', !was); b.textContent = lbT(!was) });
    stats(); toast(was ? 'Rimossa dalla lista' : 'Aggiunta alla lista');
    if (tab === 'list') render();
  },
  lrm(v) { L.lst = JSON.stringify(J('lst', []).filter(x => x != +v)); tap(500); render() },
  lclr() { if (!confirm('Svuotare tutta la lista?')) return; L.lst = '[]'; tap(500); render() },
  lwa() { if (!lstItems().length) return; window.open('https://wa.me/?text=' + encodeURIComponent(lstText(true)), '_blank', 'noopener') },
  ltg() { if (!lstItems().length) return; window.open('https://t.me/share/url?url=' + encodeURIComponent(siteUrl()) + '&text=' + encodeURIComponent(lstText(false)), '_blank', 'noopener') },
    async lmkcard() {
    const it = lstItems(); if (!it.length) return;
    const c = document.createElement('canvas'); c.width = 900; c.height = 240 + it.length * 88;
    const g = c.getContext('2d'); g.fillStyle = '#0B1120'; g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = '#10B981'; g.font = 'bold 34px sans-serif'; g.fillText('352 PRONOSTICI · LA MIA LISTA', 44, 68);
    g.fillStyle = '#8A97AD'; g.font = '22px sans-serif'; g.fillText(`${it.length} eventi selezionati · Solo uso statistico 18+`, 44, 106);
    it.forEach((m, i) => {
      const y = 145 + i * 88, pp = m.pronostico_principale || {};
      g.fillStyle = '#131C31'; g.beginPath(); g.roundRect(36, y, 828, 72, 16); g.fill();
      g.fillStyle = '#E6EDF7'; g.font = 'bold 24px sans-serif'; g.fillText(`${m.casa} - ${m.trasf}`.slice(0, 36), 56, y + 44);
      g.fillStyle = '#10B981'; g.font = 'bold 24px sans-serif'; g.textAlign = 'right'; g.fillText(`${pp.esito || '-'} · ${pp.probabilita || ''}%`, 844, y + 44); g.textAlign = 'left';
    });
    lcardUrl = c.toDataURL('image/png'); render();
  },
  ldl() { if (!lcardUrl) return; const a = document.createElement('a'); a.href = lcardUrl; a.download = '352-lista.png'; a.click(); },
 
  vote(v) { const [id, x] = v.split('|'), m = D.find(y => y.id == id), p = J('poll', {}); p[id] = x; L.poll = JSON.stringify(p); tap(740); if (m) $('#poll').innerHTML = pollBox(m) },
  theme() { const d = document.documentElement, t = d.dataset.theme === 'dark' ? 'light' : 'dark'; d.dataset.theme = t; L.theme = t; document.querySelector('meta[name=theme-color]').content = t === 'dark' ? '#0B1120' : '#F1F5FB'; render() },
  fx() { tap(); openNP() },
  npclose() { $('#np')?.classList.remove('open') },
  fxtog() { L.fx = fx() ? '0' : '1'; $('#fxb').classList.toggle('on', fx()); if ($('#np')?.classList.contains('open')) $('#np').innerHTML = npHTML(); toast(fx() ? 'Suoni e vibrazione attivi' : 'Suoni e vibrazione spenti'); tap() },
  fres() { F.res = !F.res; render() },
     fsurp() { F.surp = !F.surp; refreshList(); },

  lvall() { liveOnly = false; render() }, lvana() { liveOnly = true; render() },
  wf(v) { winF = v; render() },
  wshare(v) { const c = winCards().list.find(x => x.k === v); if (c) share(winText(c), siteUrl()) },
  simstd() { if (!isAdmin()) return; simStd = !simStd; tap(700); toast(simStd ? 'Vista Standard simulata' : 'Tornato Admin'); render() },
  async mkstory(v) { const m = D.find(x => x.id == v); if (!m) return; toast('Creo la card…'); storyBlob = await makeStory(m); storyUrl = URL.createObjectURL(storyBlob); const o = $('#stout'); if (o) o.innerHTML = storyHTML() },
  dlstory() { const a = document.createElement('a'); a.href = storyUrl; a.download = '352-partita.png'; a.click() },
  async shstory() { const f = new File([storyBlob], '352-partita.png', { type: 'image/png' }); if (navigator.canShare?.({ files: [f] })) { try { await navigator.share({ files: [f], title: '352 Pronostici' }) } catch { } } else A.dlstory() },
  share() { share('352 Pronostici - Analisi & Statistiche Calcio', siteUrl()) },
  enter() { L.ok18 = 1; $('#welcome').classList.remove('open') },
  install() { if (dip) { dip.prompt(); dip.userChoice?.finally(() => { dip = null; instUI() }) } else if (IOS) $('#ios').classList.add('open'); else toast('Usa il menu del browser: Installa app') },
  closeios() { $('#ios').classList.remove('open') },
  best() { G.best = !G.best; render() }, risk(v) { G.risk = v; render() }, gday(v) { G.day = v; render() },
  mkt(v) { G.m = G.m.includes(v) ? G.m.filter(x => x != v) : [...G.m, v]; render() },
  gen() {
    const vip = isVip(), c = dget('gc', { n: 0, s: 0 });
    if (!vip && c.n >= FREE.gen) return showVip('gen');
    tap(); genera();
    if (!vip && out.length) { c.n++; dput('gc', c) }   // una generazione a vuoto non consuma il limite
    render();
  },
  swap(v) {
    const i = +v; if (!out || !out[i]) return;
    const vip = isVip(), c = dget('gc', { n: 0, s: 0 });
    if (!vip && c.s >= FREE.swap) return showVip('swap');
    const used = new Set(out.map(o => o.m.id)), cand = POOL.filter(p => !used.has(p.m.id));
    if (!cand.length) return toast('Nessun altro evento disponibile');
    out[i] = cand[Math.floor(Math.random() * Math.min(cand.length, 6))];
    if (!vip) { c.s++; dput('gc', c) }
    cardUrl = ''; cardBlob = null; tap(700); render();
  },
  savec() {
    if (!out?.length) return;
    const sv = J('saved', []);
    if (!isVip() && sv.length >= FREE.saved) return showVip('save');
    sv.unshift({ t: Date.now(), it: out.map(o => ({ c: o.m.casa, t: o.m.trasf, sc: o.m.stemma_casa, st: o.m.stemma_trasf, x: o.x, v: o.v })) });
    L.saved = JSON.stringify(sv.slice(0, 200)); tap(800); toast('Combinazione salvata'); render();
  },
  delc(v) { const sv = J('saved', []); sv.splice(+v, 1); L.saved = JSON.stringify(sv); tap(); render() },
  async cp() { const ok = await share(gtext()); if (ok) { const b = $('#cpb'); if (b) { b.classList.add('ok'); b.innerHTML = ic('check') + 'Copiato!'; setTimeout(() => { b.classList.remove('ok'); b.innerHTML = ic('copy') + 'Copia / Condividi' }, 1800) } } },
  async mkcard() { if (!out?.length) return; toast('Creo la card…'); cardBlob = await makeCard(); cardUrl = URL.createObjectURL(cardBlob); $('#cardout').innerHTML = cardHTML() },
  dl() { const a = document.createElement('a'); a.href = cardUrl; a.download = '352-pronostici.png'; a.click() },
  async shimg() { const f = new File([cardBlob], '352-pronostici.png', { type: 'image/png' }); if (navigator.canShare?.({ files: [f] })) { try { await navigator.share({ files: [f], title: '352 Pronostici' }) } catch { } } else A.dl() },
  async refresh() { tap(); try { await refreshLive(true) } catch { toast('Aggiornamento non riuscito') } },
  totop() { scrollTo({ top: 0, behavior: 'smooth' }) },
  /* VIP */
  adminon() { L.vipAdmin = '1'; tap(880); toast('Admin Creatore attivo'); render(); scrollTo(0, 0) },
  adminoff() { L.removeItem('vipAdmin'); simStd = false; tap(); toast('Accesso Admin disattivato'); render() },
  vipclose() { $('#vipm').classList.remove('open') },
  vipgo() { A.vipclose(); A.npclose(); A.close(); tab = 'vip'; render(); scrollTo(0, 0) },
  vipsel(v) { vipSel = +v; tap(700); render(); $('#vsum')?.scrollIntoView({ behavior: 'smooth', block: 'center' }) },
  async copycause() {
    const p = VIP_PLANS.find(x => x.days === vipSel); if (!p) return;
    try { await navigator.clipboard.writeText(p.cause); tap(880); toast('Causale copiata: ' + p.cause) } catch { toast('Copia non riuscita: ' + p.cause) }
  },
  async vipact() {
    const inp = $('#vcode'); if (!inp) return;
    const raw = inp.value.trim(); if (!raw) return toast('Inserisci il codice');
    const hh = await sha(raw); if (!hh) return toast('Attivazione disponibile solo su connessione sicura (https)');
    if (hh === VIP_ADMIN_HASH) return A.adminon();
    let days = 0; for (const [d, list] of Object.entries(VIP_CODES)) if (list.includes(hh)) days = +d;
    if (!days) { tap(200); return toast('Codice non valido') }
    const used = J('vipUsed', []);
    if (used.includes(hh)) { tap(200); return toast('Codice già utilizzato su questo dispositivo') }
    L.vipExp = Math.max(Date.now(), +L.vipExp || 0) + days * 864e5;   // se già VIP, i giorni si sommano
    L.vipPlan = days; used.push(hh); L.vipUsed = JSON.stringify(used);
    tap(880); toast(`Pass VIP attivato: ${days} giorni`); render(); scrollTo(0, 0);
  }
};
document.addEventListener('click', e => { const b = e.target.closest('[data-a]'); if (b && A[b.dataset.a]) A[b.dataset.a](b.dataset.v) });
document.addEventListener('click', e => { if (e.target.id === 'np') A.npclose() });
document.addEventListener('visibilitychange', liveSync);
document.addEventListener('change', e => { if (e.target.dataset.s === 'n') G.n = +e.target.value });
document.addEventListener('input', e => { if (e.target.dataset.s === 'q') { F.q = e.target.value; refreshList() } });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { A.close(); A.vipclose(); A.npclose() }
  if (e.key === 'Enter' && e.target.id === 'vcode') A.vipact();
});
document.addEventListener('toggle', e => { if (e.target.id === 'topd') topOpen = e.target.open }, true);
addEventListener('scroll', () => { $('#top').classList.toggle('hide', scrollY < 600) }, { passive: true });

/* ---------- Avvio ---------- */
const th = L.theme || 'dark'; document.documentElement.dataset.theme = th; $('#fxb').classList.toggle('on', fx());
document.querySelector('meta[name=theme-color]').content = th === 'dark' ? '#0B1120' : '#F1F5FB';
document.documentElement.dataset.vip = isVip() ? '1' : '0';
// Sblocco rapido Admin da URL: ?vip=CODICE -> l'indirizzo viene ripulito subito, poi il codice è verificato via hash
try {
  const u = new URL(location.href), vc = u.searchParams.get('vip');
  if (vc !== null) {
    u.searchParams.delete('vip'); history.replaceState(null, '', u.pathname + u.search + u.hash);
    sha(vc).then(hh => { if (hh && hh === VIP_ADMIN_HASH) { L.vipAdmin = '1'; render(); setTimeout(() => toast('Admin Creatore attivo'), 300) } });
  }
} catch { }
document.querySelectorAll('nav [data-v=gen]').forEach(b => b.childNodes.forEach(n => { if (n.nodeType === 3) n.textContent = 'Genera' }));
if (!L.ok18) $('#welcome').classList.add('open'); instUI();
render();   // header (badge VIP) e contatore Lista subito visibili
$('#view').innerHTML = skeleton();
loadData().catch(() => { $('#view').innerHTML = `<div class="empty">${ic('refresh')}</div>` });
// scadenza VIP: se il Pass finisce mentre l'app e' aperta, torna in modalita' Standard
setInterval(() => { if (L.vipExp && !(+L.vipExp > Date.now())) { L.removeItem('vipExp'); L.removeItem('vipPlan'); render() } }, 60000);
if ('serviceWorker' in navigator) navigator.serviceWorker.register('service-worker.js').catch(() => { });
new MutationObserver(() => {
  document.querySelectorAll('input, select, textarea').forEach((el, i) => {
    if (!el.id && !el.name) el.id = el.name = 'field_' + i;
    if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', el.placeholder || el.name || 'Campo ' + (i + 1));
  });
}).observe(document.body, { childList: true, subtree: true });
