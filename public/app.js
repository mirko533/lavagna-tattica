'use strict';
const $ = s => document.querySelector(s), L = localStorage;
const J = (k, d) => { try { return JSON.parse(L[k]) ?? d } catch { return d } };
// Compliance editoriale: nessun riferimento a scommesse, quote, bookmaker, puntate o denaro
const FORB = /\b(bet\w*|scommess\w*|quot[ae]|bookmaker\w*|puntat\w*|odds?|stake|euro|denaro|soldi|jackpot)\b|[€$£]/i;
const E = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const clean = s => { s = String(s ?? ''); return FORB.test(s) ? (s.match(/[^.!?]+[.!?]*/g) || []).filter(p => !FORB.test(p)).join(' ') : s };
const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const ic = (n, c = '') => `<svg class="ic ${c}"><use href="#i-${n}"/></svg>`;
let D = [], meta = '', fav = J('fav', []), F = { c: '', f: false, t: false, top: false, q: '' }, tab = 'home', out = null, cardUrl = '', cardBlob = null;
let G = { n: 5, m: ['1X2', 'DC', 'UO', 'GN', 'MG', 'CB'], best: false, risk: 'all' };
const GR = {
  '1X2': ['1', 'X', '2'],
  DC: ['1X', 'X2', '12'],
  UO: ['U1.5', 'O1.5', 'U2.5', 'O2.5', 'U3.5', 'O3.5'],
  GN: ['GG', 'NG'],
  MG: ['MG1-2', 'MG1-3', 'MG2-3', 'MG2-4', 'MG3-5'],
  CB: ['1+O1.5', '1+O2.5', '2+O1.5', '2+O2.5', '1X+O1.5', 'X2+O1.5', '1X+GG', 'X2+GG', 'GG+O2.5', '1+GG', '2+GG', '2+U3.5'],
  MARC: ['MARC']
};
const GL = { '1X2': '1X2', DC: 'Doppia Chance', UO: 'Under/Over', GN: 'Gol/NoGol', MG: 'Multigol', CB: 'Combo', MARC: 'Marcatore' };
const lbl = k => {
  if (k.startsWith('Segna ')) return k;
  return ({ '1': 'Esito 1', X: 'Esito X', '2': 'Esito 2', GG: 'Gol', NG: 'NoGol' }[k])
    || k.replace(/U(?=\d)/g, 'Under ').replace(/O(?=\d)/g, 'Over ').replace('MG', 'Multigol ').replace('GG', 'Gol');
};

const mk = m => ({ ...(m.prob_1x2 || {}), ...(m.mercati_completi || {}) });
const LV = s => s === 'IN_PLAY' || s === 'PAUSED';
const day = m => new Date(m.data).toLocaleDateString('sv');
const tm = m => new Date(m.data).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
const dlab = d => new Date(d + 'T12:00').toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' });
const col = v => v >= 75 ? '#10B981' : v >= 60 ? '#F59E0B' : '#EF4444';   // scala cromatica affidabilita
const num = v => Math.max(0, Math.min(100, Math.round(+v || 0)));

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

/* ---------- Home ---------- */
const hay = m => norm([m.casa, m.trasf, ...(m.possibili_marcatori || []).map(p => p.giocatore), ...(m.possibili_ammoniti || []).map(p => p.giocatore), ...Object.values(m.formazioni || {}).flatMap(x => x.undici || [])].join(' '));
const vis = () => { const q = norm(F.q.trim()), td = new Date().toLocaleDateString('sv'); return D.filter(m => (!F.c || m.comp === F.c) && (!F.f || fav.includes(m.id)) && (!F.t || day(m) === td) && (!F.top || Object.values(mk(m)).some(v => v >= 80)) && (!q || hay(m).includes(q))) };
function colpo() {
  const m = D.filter(x => x.stato !== 'FINISHED' && x.affidabilita != null).sort((a, b) => b.affidabilita - a.affidabilita || (b.pronostico_principale?.probabilita || 0) - (a.pronostico_principale?.probabilita || 0))[0]; if (!m) return '';
  const pp = m.pronostico_principale || {};
  return `<div class="colpo" data-a="open" data-v="${m.id}"><div class="ch">${ic('flame')}Colpo del Giorno</div><div class="cr">${ring(m.affidabilita, 92)}<div class="cm"><div class="cp">${scudetto(m.casa, m.stemma_casa, 34)}<span>vs</span>${scudetto(m.trasf, m.stemma_trasf, 34)}</div><span class="tn">${E(m.casa)} - ${E(m.trasf)}</span>${pp.esito ? `<span class="bdg">${ic('zap')}${E(pp.esito)} · ${num(pp.probabilita)}%</span>` : ''}</div></div></div>`;
}
const tri = p => `<div class="tri"><div class="tb"><i style="flex:${num(p['1']) || 1};background:#10B981"></i><i style="flex:${num(p.X) || 1};background:#64748B"></i><i style="flex:${num(p['2']) || 1};background:#06B6D4"></i></div><div class="tl3"><span>1 · ${num(p['1'])}</span><span>X · ${num(p.X)}</span><span>2 · ${num(p['2'])}</span></div></div>`;
function card(m) {
  const lv = LV(m.stato), pp = m.pronostico_principale;
  return `<article class="card" data-a="open" data-v="${m.id}"><div class="ct"><span class="tn">${E(m.compNome)}</span></div><button class="fav ${fav.includes(m.id) ? 'on' : ''}" data-a="fav" data-v="${m.id}" aria-label="Preferita">${ic('heart')}</button>
<div class="mr"><div class="tz">${scudetto(m.casa, m.stemma_casa)}<span class="tn">${E(m.casa)}</span></div><div class="mc">${lv ? '<span class="live"><i></i>LIVE</span>' : ''}<b class="tt">${m.score ? m.score.join(' - ') : tm(m)}</b>${pp ? `<span class="bdg" style="--bc:${col(pp.probabilita)}">${E(pp.esito)} · ${num(pp.probabilita)}%</span>` : ''}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf)}<span class="tn">${E(m.trasf)}</span></div></div>${m.prob_1x2 ? tri(m.prob_1x2) : ''}</article>`;
}
function listHTML() {
  const l = vis(), ds = [...new Set(l.map(day))].sort(); let n = 0;
  return ds.length ? ds.map(d => `<h2 class="dh">${dlab(d)}</h2>` + l.filter(m => day(m) === d).map(m => card(m) + (++n % 7 === 0 ? `<div class="ad-native" ${n === 7 ? 'id="ad-native-feed"' : ''} data-slot="${n / 7}"></div>` : '')).join('')).join('') : `<div class="empty">${ic('search')}</div>`;
}
const disc = () => `<div class="disc"><b>18+</b> Contenuti esclusivamente informativi e statistici: nessuna quota, nessun invito al gioco. Vietato ai minori di 18 anni.</div>`;
function vHome() {
  const cs = [...new Map(D.map(m => [m.comp, m.compNome]))], ch = (on, a, v, i, t) => `<button class="chip ${on ? 'on' : ''}" data-a="${a}" ${v !== undefined ? `data-v="${v}"` : ''}>${i ? ic(i) : ''}${E(t)}</button>`;
  return colpo() + `<label class="search">${ic('search')}<input id="q" data-s="q" type="search" placeholder="Squadra o giocatore" value="${E(F.q)}" autocomplete="off"></label>
<div class="chips">${ch(F.t, 'ftoday', undefined, 'cal', 'Oggi')}${ch(F.top, 'ftop', undefined, 'flame', 'Top 80%+')}${ch(F.f, 'favf', undefined, 'heart', 'Preferiti')}${cs.map(([c, n]) => ch(F.c === c, 'comp', c, '', n)).join('')}</div><div id="hl">${listHTML()}</div>` + disc();
}

/* ---------- Live ---------- */
function evIc(e) { const t = norm(e.tipo || e.type || e.t || ''); return /gol|goal/.test(t) ? 'ball' : /esp|ross|red/.test(t) ? 'card' : /amm|giall|yell|card/.test(t) ? 'card' : /sost|sub/.test(t) ? 'sub' : 'ball' }
function vLive() {
  const td = new Date().toLocaleDateString('sv'), l = D.filter(m => LV(m.stato) || day(m) === td).sort((a, b) => LV(b.stato) - LV(a.stato) || a.data.localeCompare(b.data));
  return `<button class="btn" data-a="refresh">${ic('refresh')}Aggiorna Live</button><div style="height:12px"></div>` + (l.length ? l.map(m => {
    const ev = m.eventi || [];
    return `<article class="card" style="cursor:default"><div class="ct"><span class="tn">${E(m.compNome)}</span></div><div class="mr"><div class="tz">${scudetto(m.casa, m.stemma_casa)}<span class="tn">${E(m.casa)}</span></div><div class="mc">${LV(m.stato) ? '<span class="live"><i></i>LIVE</span>' : m.stato === 'FINISHED' ? '<span class="mu" style="font-size:11px;font-weight:700">FINALE</span>' : ''}<b class="tt" style="font-size:24px">${m.score ? m.score.join(' - ') : tm(m)}</b></div><div class="tz">${scudetto(m.trasf, m.stemma_trasf)}<span class="tn">${E(m.trasf)}</span></div></div>
${ev.length ? `<div class="tl">${ev.map(e => `<div>${ic(evIc(e), /esp|ross|red/.test(norm(e.tipo || e.type || '')) ? 'r' : '')}<b>${E(e.minuto ?? e.min ?? '')}'</b> ${E(e.giocatore || e.t || e.testo || '')}</div>`).join('')}</div>` : ''}</article>`
  }).join('') : `<div class="empty">${ic('live')}</div>`) + disc();
}

/* ---------- Generatore + card immagine ---------- */
const comb = () => (out.reduce((a, o) => a * o.v / 100, 1) * 100).toFixed(1);
const gtext = () => '352 Pronostici - Combinazione statistica\n' + out.map((o, i) => `${i + 1}. ${o.m.casa} - ${o.m.trasf}: ${lbl(o.x)} (${o.v}%)`).join('\n') + `\nProbabilità combinata stimata: ${comb()}%\n18+ · Solo informativo e statistico.`;
function genera() {
  const activeGroups = G.best ? Object.keys(GR) : G.m;
  const keys = activeGroups.filter(g => g !== 'MARC').flatMap(g => GR[g] || []);
  const includeMarc = activeGroups.includes('MARC');
   const [lo, hi] = {
    prud:,
    bil: [60, 74.9],
    alto: [40, 59.9],
    estr: [18, 44.9],
    all: [0, 100]
  }[G.risk] || [60, 74.9];


  const pool = [];
  D.filter(m => m.stato !== 'FINISHED' && m.prob_1x2).forEach(m => {
    const k = mk(m);
    const validi = [];

    keys.forEach(x => {
      const v = +k[x];
      if (v >= lo && v <= hi) validi.push({ x, v });
    });

    if (includeMarc && Array.isArray(m.possibili_marcatori)) {
      m.possibili_marcatori.forEach(p => {
        const v = +p.prob;
        if (p.giocatore && v >= lo && v <= hi) {
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

  out = pool.sort((a, b) => b.peso - a.peso).slice(0, G.n);
  cardUrl = '';
  cardBlob = null;
}

function vGen() {
  return `<div class="box"><h3>${ic('sliders')}Parametri</h3>
<div class="row"><label>Eventi</label><select data-s="n">${[2, 3, 4, 5, 6, 7, 8].map(n => `<option ${G.n == n ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
<div class="row"><button class="chip ${G.best ? 'on' : ''}" data-a="best">${ic('zap')}Mix Completo (Tutti i mercati)</button></div>
<div class="row" style="${G.best ? 'opacity:.4;pointer-events:none' : ''}"><label>Mercati</label>${Object.keys(GR).map(g => `<button class="chip ${G.m.includes(g) ? 'on' : ''}" data-a="mkt" data-v="${g}">${GL[g]}</button>`).join('')}</div>
<div class="row"><label>Livello di rischio</label>${[
    ['prud', 'Prudente >75%'],
    ['bil', 'Bilanciato 60-74%'],
    ['alto', 'Alto Rischio 40-59%'],
    ['estr', 'Estremo <45%'],
    ['all', 'Tutti']
  ].map(([v, l]) => `<button class="chip ${G.risk === v ? 'on' : ''}" data-a="risk" data-v="${v}">${l}</button>`).join('')}</div>
<button class="btn" data-a="gen">${ic('gen')}Genera Nuova Combinazione</button></div>` +
    (out ? (out.length ? `<div class="box"><h3>${ic('target')}Combinazione statistica</h3>${out.map(o => `<div class="sg"><div class="pz">${scudetto(o.m.casa, o.m.stemma_casa, 24)}${scudetto(o.m.trasf, o.m.stemma_trasf, 24)}<span class="tn">${E(o.m.casa)} - ${E(o.m.trasf)}</span></div><span class="bdg" style="--bc:${col(o.v)}">${E(lbl(o.x))} · ${o.v}%</span></div>`).join('')}<div style="display:flex;align-items:center;gap:12px;margin-top:12px">${ring(Math.round(comb()), 64, 7)}<span class="mu" style="font-size:12px">Probabilità combinata stimata</span></div>
<button class="btn s" id="cpb" data-a="cp">${ic('copy')}Copia / Condividi</button><button class="btn" data-a="mkcard">${ic('img')}Crea Card Immagine</button><div id="cardout">${cardUrl ? cardHTML() : ''}</div></div>` : `<div class="empty">${ic('search')}</div>`) : '') + disc();
}

const cardHTML = () => `<img class="cimg" src="${cardUrl}" alt="Card 352 Pronostici"><button class="btn s" data-a="dl">${ic('down')}Scarica PNG</button><button class="btn s" data-a="shimg">${ic('share')}Condividi immagine</button>`;
async function makeCard() {
  try { await document.fonts?.ready } catch { }
  const n = out.length, W = 1080, H = 400 + n * 150 + 150, cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d'), FN = "'Plus Jakarta Sans',system-ui,sans-serif";
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
  x.textAlign = 'left'; x.fillStyle = '#fff'; x.font = `800 60px ${FN}`; x.fillText('352 Pronostici', 180, 122); x.fillStyle = '#8A97AD'; x.font = `600 30px ${FN}`; x.fillText('Combinazione statistica · ' + new Date().toLocaleDateString('it-IT', { day: 'numeric', month: 'long' }), 180, 170);
  out.forEach((o, i) => {
    const y = 250 + i * 150, v = o.v; x.fillStyle = 'rgba(255,255,255,.07)'; rr(50, y, 980, 130, 28); x.fill(); x.strokeStyle = 'rgba(255,255,255,.1)'; x.lineWidth = 2; x.stroke();
    cShield(75, y + 22, 62, o.m.casa, o.m.stemma_casa); cShield(150, y + 22, 62, o.m.trasf, o.m.stemma_trasf);
    x.textAlign = 'left'; x.fillStyle = '#fff'; x.font = `800 34px ${FN}`; x.fillText(fit(`${o.m.casa} - ${o.m.trasf}`, 540), 240, y + 56); x.fillStyle = '#8A97AD'; x.font = `600 28px ${FN}`; x.fillText(lbl(o.x), 240, y + 92);
    x.fillStyle = 'rgba(255,255,255,.12)'; rr(240, y + 106, 540, 9, 5); x.fill(); x.fillStyle = col(v); rr(240, y + 106, 540 * v / 100, 9, 5); x.fill();
    x.textAlign = 'right'; x.fillStyle = col(v); x.font = `800 64px ${FN}`; x.fillText(v + '%', 1000, y + 82);
  });
  const fy = 250 + n * 150 + 30; x.textAlign = 'left'; x.fillStyle = '#FBBF24'; x.font = `800 40px ${FN}`; x.fillText(`Probabilità combinata stimata: ${comb()}%`, 60, fy + 40); x.fillStyle = '#8A97AD'; x.font = `600 26px ${FN}`; x.fillText('18+ · Contenuto solo informativo e statistico', 60, fy + 92);
  return new Promise(r => cv.toBlob(b => r(b), 'image/png'));
}

/* ---------- Info ---------- */
function vInfo() {
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  return `<div class="ig"><div class="ib2">${ic('chart')}Probabilità e affidabilità</div><div class="ib2">${ic('users')}Rose ufficiali aggiornate</div><div class="ib2">${ic('shield')}Nessun dato personale</div><div class="ib2"><div class="age" style="width:34px;height:34px;font-size:12px;margin:0 auto 8px">18+</div>Solo maggiorenni</div></div>
<div class="box"><h3>${ic('info')}Come leggere i dati</h3><p class="mu" style="font-size:13px">Un modello AI stima le probabilità usando forma, classifica e rose. Sono stime statistiche, non certezze. Nessuna quota, nessun invito al gioco; gli scudetti sono generati dai colori sociali.</p></div>
${standalone ? '' : `<button class="btn" data-a="install">${ic('down')}Installa App</button>`}` + disc();
}

/* ---------- Scheda partita ---------- */
const pollBox = m => { const v = J('poll', {})[m.id], p = m.prob_1x2 || {}; return `<h3>${ic('users')}Sondaggio rapido</h3><div class="pollb">${['1', 'X', '2'].map(x => `<button class="pv ${v === x ? 'on' : ''}" data-a="vote" data-v="${m.id}|${x}">${x}</button>`).join('')}</div>${v ? ['1', 'X', '2'].map(x => `<div class="cmp"><b>${x}</b><div class="cb"><u style="width:${num(p[x])}%;background:#06B6D4"></u>${v === x ? '<s class="you">TU</s>' : ''}</div><span>AI ${num(p[x])}%</span></div>`).join('') : ''}` };
function sheet(m) {
  const pp = m.pronostico_principale, k = mk(m), mc = m.mercati_completi || {}, pl = (arr, cl, i) => (arr || []).map(p => `<div class="pp ${cl}">${ic(i)}<div class="pn"><b class="tn">${E(p.giocatore)}</b><small class="tn">${E(p.squadra === 'casa' ? m.casa : m.trasf)}</small></div><div class="pbr"><u style="--w:${num(p.prob)}%"></u></div><span>${num(p.prob)}%</span></div>`).join('');
  const ig = Math.round(((+k['O2.5'] || 0) + (+k.GG || 0)) / 2);
  $('#sbody').innerHTML = `<div class="sh2"><div class="tz">${scudetto(m.casa, m.stemma_casa, 52)}<span class="tn">${E(m.casa)}</span></div><div class="sc">${m.score ? m.score.join(' - ') : tm(m)}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf, 52)}<span class="tn">${E(m.trasf)}</span></div></div>
<p class="mu" style="text-align:center;font-size:12px">${E(m.compNome)} · ${dlab(day(m))}</p>
${pp ? `<div class="hero">${ring(pp.probabilita, 96, 11)}<div class="hi"><small>${ic('target')}PRONOSTICO CONSIGLIATO</small><div class="hx tn">${E(String(pp.esito).toUpperCase())}</div>${pp.motivazione_breve ? `<span class="mp">${E(clean(pp.motivazione_breve))}</span>` : ''}</div></div>` : ''}
${m.prob_1x2 ? `<div class="box"><h3>${ic('chart')}Affidabilità e Indice Gol</h3><div class="gg">${gauge(m.affidabilita)}<div><div class="pl"><span>${ic('flame', '')}Indice Gol ${num(ig)}</span></div><div class="pt"><b style="--w:${num(ig)}%;background:${col(ig)}"></b></div></div></div></div>
<div class="box"><h3>${ic('live')}Probabilità</h3>${bar([{ l: '1', v: k['1'], c: '#10B981' }, { l: 'X', v: k.X, c: '#64748B' }, { l: '2', v: k['2'], c: '#06B6D4' }])}${bar([{ l: 'Gol', v: k.GG, c: '#10B981' }, { l: 'NoGol', v: k.NG, c: '#EF4444' }])}${bar([{ l: 'Under 2.5', v: k['U2.5'], c: '#8B5CF6' }, { l: 'Over 2.5', v: k['O2.5'], c: '#F59E0B' }])}</div>
<div class="box"><h3>${ic('sliders')}Mercati e Combo</h3><div class="tiles">${Object.entries(mc).map(([x, v]) => `<div class="tile" style="--h:${Math.round(Math.min(num(v), 100) * 1.4)};--w:${num(v)}%"><b>${E(x)}</b><span>${num(v)}%</span><i></i></div>`).join('')}</div></div>
${pitch(m) ? `<div class="box"><h3>${ic('users')}Probabili formazioni</h3>${pitch(m)}</div>` : ''}
<div class="box"><h3>${ic('ball')}Probabili marcatori</h3>${pl(m.possibili_marcatori, 'g', 'ball') || '<p class="mu">–</p>'}</div>
<div class="box"><h3>${ic('card')}Rischio cartellino</h3>${pl(m.possibili_ammoniti, 'y', 'card') || '<p class="mu">–</p>'}</div>
<div class="ad-sheet" id="ad-sheet-bottom"></div>
<div class="box" id="poll">${pollBox(m)}</div>
<details class="acc"><summary>${ic('file')}Dettagli testuali AI${ic('chev')}</summary><p>${E(clean(m.analisi))}</p></details>` : `<div class="empty">${ic('search')}</div>`}${disc()}`;
  $('#sheet').dataset.id = m.id; $('#sheet').scrollTop = 0; $('#sheet').classList.add('open'); $('#scrim').classList.add('open');
}

/* ---------- Render e stato ---------- */
function stats() {
  const up = meta ? new Date(meta).toLocaleString('it-IT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '–';
  $('#upd').textContent = `Agg. ${up} · ${D.length} partite · ${D.filter(m => LV(m.stato)).length} live · ${fav.length} ★`;
}
function render() { $('#view').innerHTML = { home: vHome, live: vLive, gen: vGen, info: vInfo }[tab](); document.querySelectorAll('nav button').forEach(b => b.classList.toggle('on', b.dataset.v === tab)); stats() }
const skeleton = () => '<div class="sk"></div>'.repeat(4);
async function loadData(toastOk) {
  const r = await fetch('data/matches.json?t=' + Date.now(), { cache: 'no-store' }); const j = await r.json();
  D = j.matches || []; meta = j.aggiornato_il || ''; render(); if (toastOk) toast('Dati aggiornati');
}

/* ---------- Installa app ---------- */
let dip = null; const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone, IOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
const instUI = () => $('#inst').classList.toggle('hide', standalone() || !(dip || IOS));
addEventListener('beforeinstallprompt', e => { e.preventDefault(); dip = e; instUI() });
addEventListener('appinstalled', () => { dip = null; instUI() });

/* ---------- Azioni ---------- */
const A = {
  tab(v) { tap(520); tab = v; render(); scrollTo(0, 0) },
  comp(v) { F.c = v; render() }, favf() { F.f = !F.f; render() }, ftoday() { F.t = !F.t; render() }, ftop() { F.top = !F.top; render() },
  open(v) { const m = D.find(x => x.id == v); if (m) { tap(); sheet(m) } },
  close() { $('#sheet').classList.remove('open'); $('#scrim').classList.remove('open') },
  fav(v) { v = +v; tap(880); fav = fav.includes(v) ? fav.filter(x => x != v) : [...fav, v]; L.fav = JSON.stringify(fav); if (F.f) return render(); document.querySelectorAll(`[data-a=fav][data-v="${v}"]`).forEach(b => b.classList.toggle('on', fav.includes(v))); stats() },
  vote(v) { const [id, x] = v.split('|'), m = D.find(y => y.id == id), p = J('poll', {}); p[id] = x; L.poll = JSON.stringify(p); tap(740); if (m) $('#poll').innerHTML = pollBox(m) },
  theme() { const d = document.documentElement, t = d.dataset.theme === 'dark' ? 'light' : 'dark'; d.dataset.theme = t; L.theme = t; $('#th').innerHTML = ic(t === 'dark' ? 'sun' : 'moon'); document.querySelector('meta[name=theme-color]').content = t === 'dark' ? '#0B1120' : '#F1F5FB' },
  fx() { L.fx = fx() ? '0' : '1'; $('#fxb').classList.toggle('on', fx()); toast(fx() ? 'Suoni e vibrazione attivi' : 'Suoni e vibrazione spenti'); tap() },
  share() { share('352 Pronostici - Analisi & Statistiche Calcio', location.href.split('#')[0]) },
  enter() { L.ok18 = 1; $('#welcome').classList.remove('open') },
  install() { if (dip) { dip.prompt(); dip.userChoice?.finally(() => { dip = null; instUI() }) } else if (IOS) $('#ios').classList.add('open'); else toast('Usa il menu del browser: Installa app') },
  closeios() { $('#ios').classList.remove('open') },
  best() { G.best = !G.best; render() }, risk(v) { G.risk = v; render() },
  mkt(v) { G.m = G.m.includes(v) ? G.m.filter(x => x != v) : [...G.m, v]; render() },
  gen() { tap(); genera(); render() },
  async cp() { const ok = await share(gtext()); if (ok) { const b = $('#cpb'); if (b) { b.classList.add('ok'); b.innerHTML = ic('check') + 'Copiato!'; setTimeout(() => { b.classList.remove('ok'); b.innerHTML = ic('copy') + 'Copia / Condividi' }, 1800) } } },
  async mkcard() { if (!out?.length) return; toast('Creo la card…'); cardBlob = await makeCard(); cardUrl = URL.createObjectURL(cardBlob); $('#cardout').innerHTML = cardHTML() },
  dl() { const a = document.createElement('a'); a.href = cardUrl; a.download = '352-pronostici.png'; a.click() },
  async shimg() { const f = new File([cardBlob], '352-pronostici.png', { type: 'image/png' }); if (navigator.canShare?.({ files: [f] })) { try { await navigator.share({ files: [f], title: '352 Pronostici' }) } catch { } } else A.dl() },
  async refresh() { tap(); try { await loadData(true) } catch { toast('Aggiornamento non riuscito') } }
};
document.addEventListener('click', e => { const b = e.target.closest('[data-a]'); if (b && A[b.dataset.a]) A[b.dataset.a](b.dataset.v) });
document.addEventListener('change', e => { if (e.target.dataset.s === 'n') G.n = +e.target.value });
document.addEventListener('input', e => { if (e.target.dataset.s === 'q') { F.q = e.target.value; $('#hl').innerHTML = listHTML() } });
document.addEventListener('keydown', e => { if (e.key === 'Escape') A.close() });

/* ---------- Avvio ---------- */
const th = L.theme || 'dark'; document.documentElement.dataset.theme = th; $('#th').innerHTML = ic(th === 'dark' ? 'sun' : 'moon'); $('#fxb').classList.toggle('on', fx());
if (!L.ok18) $('#welcome').classList.add('open'); instUI();
$('#view').innerHTML = skeleton();
loadData().catch(() => { $('#view').innerHTML = `<div class="empty">${ic('refresh')}</div>` });
if ('serviceWorker' in navigator) navigator.serviceWorker.register('service-worker.js').catch(() => { });
