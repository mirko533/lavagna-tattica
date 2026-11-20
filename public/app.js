'use strict';
const $ = s => document.querySelector(s), L = localStorage;
const J = (k, d) => { try { return JSON.parse(L[k]) ?? d } catch { return d } };
// Compliance editoriale: nessun riferimento a scommesse, quote, bookmaker, puntate o denaro
const FORB = /\b(bet\w*|scommess\w*|quot[ae]|bookmaker\w*|puntat\w*|odds?|stake|euro|denaro|soldi|jackpot)\b|[€$£]/i;
const E = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const clean = s => { s = String(s ?? ''); return FORB.test(s) ? (s.match(/[^.!?]+[.!?]*/g) || []).filter(p => !FORB.test(p)).join(' ') : s };
const ic = (n, c = '') => `<svg class="ic ${c}"><use href="#i-${n}"/></svg>`;
let D = [], meta = '', fav = J('fav', []), F = { c: '', f: false }, tab = 'home', openId = null, out = null, TL = {};
let G = { n: 5, m: ['1X2', 'DC', 'UO'], best: false, risk: 'all' };
const GR = { '1X2': ['1', 'X', '2'], DC: ['1X', 'X2', '12'], UO: ['U1.5', 'O1.5', 'U2.5', 'O2.5', 'U3.5', 'O3.5'], GN: ['GG', 'NG'], MG: ['MG1-3', 'MG2-4'], CB: ['1+O1.5', '1X+GG', '2+U3.5'] };
const GL = { '1X2': '1X2', DC: 'Doppia Chance', UO: 'Under/Over', GN: 'Gol/NoGol', MG: 'Multigol', CB: 'Combo' };
const lbl = k => ({ '1': 'Esito 1', X: 'Esito X', '2': 'Esito 2', GG: 'Gol', NG: 'NoGol' }[k]) || k.replace(/U(?=\d)/g, 'Under ').replace(/O(?=\d)/g, 'Over ').replace('MG', 'Multigol ').replace('GG', 'Gol');
const mk = m => ({ ...(m.prob_1x2 || {}), ...(m.mercati_completi || {}) });
const LV = s => s === 'IN_PLAY' || s === 'PAUSED';
const day = m => new Date(m.data).toLocaleDateString('sv');
const tm = m => new Date(m.data).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
const dlab = d => new Date(d + 'T12:00').toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' });

/* ---------- Scudetto SVG dinamico (colori e pattern reali, niente loghi protetti) ---------- */
const PAL = ['#1d4ed8', '#b91c1c', '#047857', '#7c3aed', '#b45309', '#0e7490'];
const isHex = c => /^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(c || '');
const lum = h => { h = h.replace('#', ''); if (h.length == 3) h = [...h].map(x => x + x).join(''); const [r, g, b] = [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16) / 255).map(v => v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4); return .2126 * r + .7152 * g + .0722 * b };
let sid = 0;
function scudetto(name, st, s = 40) {
  const id = 'sc' + (++sid), c = (st?.colori || []).filter(isHex), h = [...name].reduce((a, x) => (a * 31 + x.charCodeAt(0)) % 997, 0);
  const c1 = c[0] || PAL[h % 6], c2 = c[1] || '#f8fafc', p = ['vertical', 'horizontal', 'diagonal', 'half', 'solid'].includes(st?.pattern) ? st.pattern : 'solid';
  const R = (x, y, w, hh, f) => `<rect x="${x}" y="${y}" width="${w}" height="${hh}" fill="${f}"/>`;
  const body = {
    vertical: R(0, 0, 40, 46, c1) + R(14.3, 0, 11.4, 46, c2),
    horizontal: R(0, 0, 40, 46, c1) + R(0, 17, 40, 14, c2),
    diagonal: R(0, 0, 40, 46, c1) + `<polygon points="34,-4 56,-4 -4,56 -4,34" fill="${c2}"/>`,
    half: R(0, 0, 20, 46, c1) + R(20, 0, 20, 46, c2),
    solid: R(0, 0, 40, 46, c1)
  }[p];
  const cen = p === 'solid' ? lum(c1) : p === 'half' ? (lum(c1) + lum(c2)) / 2 : lum(c2), tc = cen > .45 ? '#0B1120' : '#ffffff';
  const sig = name.normalize('NFD').replace(/[^A-Za-z ]/g, '').trim().slice(0, 3).toUpperCase();
  return `<svg width="${s}" height="${Math.round(s * 1.15)}" viewBox="0 0 40 46" aria-hidden="true"><defs><clipPath id="${id}"><path d="M3 3h34v21c0 11-8 17-17 20C11 41 3 35 3 24z"/></clipPath></defs><g clip-path="url(#${id})">${body}<rect x="3" y="3" width="34" height="8" fill="#000" opacity=".12"/></g><path d="M3 3h34v21c0 11-8 17-17 20C11 41 3 35 3 24z" fill="none" stroke="${p === 'solid' ? c2 : 'rgba(255,255,255,.55)'}" stroke-width="2"/><text x="20" y="28" text-anchor="middle" font-size="${sig.length > 2 ? 12 : 14}" font-weight="800" fill="${tc}" font-family="Plus Jakarta Sans,sans-serif">${E(sig)}</text></svg>`;
}

/* ---------- Componenti ---------- */
const disc = () => `<div class="disc"><b>18+</b> Contenuti esclusivamente informativi e statistici: nessuna quota, nessun invito al gioco. Vietato ai minori di 18 anni. Il gioco può causare dipendenza patologica.</div>`;
const toast = s => { const e = $('#toast'); e.textContent = s; e.classList.add('on'); setTimeout(() => e.classList.remove('on'), 1800) };
async function share(text, url) { if (navigator.share) { try { await navigator.share({ title: '352 Pronostici', text, url }); return true } catch { return false } } try { await navigator.clipboard.writeText(url ? text + '\n' + url : text); toast('Copiato!'); return true } catch { return false } }
const bar = segs => `<div class="pb"><div class="pl">${segs.map(s => `<span><i style="background:${s.c}"></i>${s.l} ${s.v}%</span>`).join('')}</div><div class="pt">${segs.map(s => `<b style="--w:${s.v}%;background:${s.c}">${s.v >= 14 ? s.v + '%' : ''}</b>`).join('')}</div></div>`;
const skeleton = () => '<div class="sk"></div>'.repeat(4);

function card(m) {
  const lv = LV(m.stato), pp = m.pronostico_principale;
  return `<article class="card" data-a="open" data-v="${m.id}"><div class="ct"><span class="tn mu">${E(m.compNome)}</span>${lv ? '<span class="live"><i></i>LIVE</span>' : `<span class="mu">${tm(m)}</span>`}<button class="fav ${fav.includes(m.id) ? 'on' : ''}" data-a="fav" data-v="${m.id}" aria-label="Preferita">${ic('heart')}</button></div>
<div class="tm2"><div class="tz">${scudetto(m.casa, m.stemma_casa)}<span class="tn">${E(m.casa)}</span></div><div class="sc">${m.score ? m.score.join(' - ') : 'vs'}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf)}<span class="tn">${E(m.trasf)}</span></div></div>
${pp ? `<div class="pill">${ic('zap')}<b>${E(pp.esito)}</b><span>${E(pp.probabilita)}%</span></div>` : ''}</article>`;
}

/* ---------- Viste ---------- */
function vHome() {
  const cs = [...new Map(D.map(m => [m.comp, m.compNome]))], l = D.filter(m => (!F.c || m.comp === F.c) && (!F.f || fav.includes(m.id))), ds = [...new Set(l.map(day))].sort();
  return `<div class="chips"><button class="chip ${F.f ? 'on' : ''}" data-a="favf">${ic('heart')}Solo preferite</button><button class="chip ${!F.c && !F.f ? 'on' : ''}" data-a="comp" data-v="">${ic('trophy')}Tutte</button>${cs.map(([c, n]) => `<button class="chip ${F.c === c ? 'on' : ''}" data-a="comp" data-v="${c}">${E(n)}</button>`).join('')}</div>` +
    (ds.length ? ds.map(d => `<h2 class="dh">${dlab(d)} · ${l.filter(m => day(m) === d).length} partite</h2>` + l.filter(m => day(m) === d).map(card).join('')).join('') : `<p class="empty">Nessuna partita disponibile con questi filtri.</p>`) + disc();
}
function vLive() {
  const td = new Date().toLocaleDateString('sv'), l = D.filter(m => LV(m.stato) || day(m) === td).sort((a, b) => LV(b.stato) - LV(a.stato) || a.data.localeCompare(b.data));
  return `<h2 class="dh" style="font-size:17px;color:var(--tx)">Live e risultati di oggi</h2><button class="btn" data-a="refresh">${ic('refresh')}Aggiorna Live</button><div style="height:12px"></div>` +
    (l.length ? l.map(m => `<article class="card" style="cursor:default"><div class="ct"><span class="tn mu">${E(m.compNome)}</span>${LV(m.stato) ? '<span class="live"><i></i>LIVE</span>' : `<span class="mu">${m.stato === 'FINISHED' ? 'Finale' : tm(m)}</span>`}</div>
<div class="tm2"><div class="tz">${scudetto(m.casa, m.stemma_casa)}<span class="tn">${E(m.casa)}</span></div><div class="sc" style="color:var(--tx)">${m.score ? m.score.join(' - ') : 'vs'}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf)}<span class="tn">${E(m.trasf)}</span></div></div>
<button class="chip" style="margin-top:10px" data-a="ev" data-v="${m.id}">${ic('live')}Marcatori ed eventi</button><div id="tl${m.id}">${TL[m.id] || ''}</div></article>`).join('') : '<p class="empty">Nessuna partita in programma oggi.</p>') + disc();
}
function vGen() {
  return `<div class="box"><h3>${ic('sliders')}Parametri del generatore</h3>
<div class="row"><label>Numero di eventi</label><select data-s="n">${[2, 3, 4, 5, 6, 7, 8].map(n => `<option ${G.n == n ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
<div class="row"><label>Modalità</label><button class="chip ${G.best ? 'on' : ''}" data-a="best">${ic('zap')}Miglior Esito Statistico</button></div>
<div class="row" style="${G.best ? 'opacity:.4;pointer-events:none' : ''}"><label>Mercati</label>${Object.keys(GR).map(g => `<button class="chip ${G.m.includes(g) ? 'on' : ''}" data-a="mkt" data-v="${g}">${GL[g]}</button>`).join('')}</div>
<div class="row"><label>Livello di rischio</label>${[['prud', 'Prudente >75%'], ['bil', 'Bilanciato 60-75%'], ['all', 'Tutti']].map(([v, l]) => `<button class="chip ${G.risk === v ? 'on' : ''}" data-a="risk" data-v="${v}">${l}</button>`).join('')}</div>
<button class="btn" data-a="gen">${ic('gen')}Genera combinazione statistica</button></div>` +
    (out ? (out.length ? `<div class="box"><h3>Combinazione statistica</h3>${out.map((o, i) => `<div class="pr"><span>${i + 1}. ${E(o.m.casa)} - ${E(o.m.trasf)}<small>${E(lbl(o.x))}</small></span><b class="v">${o.v}%</b></div>`).join('')}<p class="mu" style="margin-top:10px;font-size:13px">Probabilità combinata stimata: <b style="color:var(--go)">${comb()}%</b></p><button class="btn s" id="cpb" data-a="cp">${ic('copy')}Copia / Condividi combinazione</button></div>` : '<p class="empty">Nessun evento con questi filtri: prova un livello di rischio diverso.</p>') : '') + disc();
}
const comb = () => (out.reduce((a, o) => a * o.v / 100, 1) * 100).toFixed(1);
const gtext = () => '352 Pronostici - Combinazione statistica\n' + out.map((o, i) => `${i + 1}. ${o.m.casa} - ${o.m.trasf}: ${lbl(o.x)} (${o.v}%)`).join('\n') + `\nProbabilità combinata stimata: ${comb()}%\n18+ · Solo informativo e statistico.`;
function genera() {
  const keys = G.best ? Object.values(GR).flat() : G.m.flatMap(g => GR[g]), lo = { prud: 75.01, bil: 60, all: 0 }[G.risk], hi = { prud: 101, bil: 75, all: 101 }[G.risk], c = [];
  D.filter(m => m.stato !== 'FINISHED' && m.prob_1x2).forEach(m => { const k = mk(m); let b = null; keys.forEach(x => { const v = +k[x]; if (v >= lo && v <= hi && (!b || v > b.v)) b = { x, v } }); if (b) c.push({ m, ...b }) });
  out = c.sort((a, b) => b.v - a.v).slice(0, G.n);
}
function vInfo() {
  return `<div class="txt"><h3>Metodologia</h3><p>Ogni partita viene analizzata da un modello di intelligenza artificiale che usa rose ufficiali aggiornate, classifica, stato di forma, rendimento in casa e in trasferta e duelli tattici. Il risultato è un insieme di probabilità percentuali e un indice di affidabilità statistica.</p><p>Le stime non sono certezze: nessun risultato è garantito. Le formazioni sono probabili e possono cambiare.</p>
<h3>Note legali</h3><p>352 Pronostici ha scopo esclusivamente informativo e statistico. Non contiene quote, non rimanda a siti di scommesse e non invita al gioco. Il servizio è vietato ai minori di 18 anni. Gli scudetti sono generati graficamente dai colori sociali: nessun logo ufficiale è utilizzato.</p>
<h3>Privacy</h3><p>Non raccogliamo dati personali. Preferiti, tema e (facoltativa) chiave API per il Live restano solo sul tuo dispositivo.</p></div>` + disc();
}
function stats() {
  const lv = D.filter(m => LV(m.stato)).length, up = meta ? new Date(meta).toLocaleString('it-IT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '–';
  $('#stats').innerHTML = `<span>${ic('cal').replace('class="ic', 'class="ic" style="width:13px;height:13px;')}Aggiornato <b>${up}</b></span><span>Partite <b>${D.length}</b></span><span>Live <b>${lv}</b></span><span>Preferite <b id="nf">${fav.length}</b></span>`;
}
function render() { $('#view').innerHTML = { home: vHome, live: vLive, gen: vGen, info: vInfo }[tab](); document.querySelectorAll('nav button').forEach(b => b.classList.toggle('on', b.dataset.v === tab)); stats() }

/* ---------- Scheda di dettaglio ---------- */
function sheet(m) {
  const pp = m.pronostico_principale, k = mk(m), f = m.formazioni || {};
  const pl = (arr, extra) => (arr || []).map(p => `<div class="pr"><span>${E(p.giocatore)} <small>${E(p.ruolo || '')} · ${E(p.squadra === 'casa' ? m.casa : m.trasf)}${extra && p.motivo ? ' · ' + E(clean(p.motivo)) : ''}</small></span><b class="v">${E(p.prob)}%</b></div>`).join('');
  $('#sbody').innerHTML = `<div class="sh2"><div class="tz">${scudetto(m.casa, m.stemma_casa, 52)}<span class="tn">${E(m.casa)}</span></div><div class="sc">${m.score ? m.score.join(' - ') : tm(m)}</div><div class="tz">${scudetto(m.trasf, m.stemma_trasf, 52)}<span class="tn">${E(m.trasf)}</span></div></div>
<p class="mu" style="text-align:center;font-size:12px">${E(m.compNome)} · ${dlab(day(m))}</p>
${pp ? `<div class="hero"><small>PRONOSTICO CONSIGLIATO</small><div class="hx">${E(String(pp.esito).toUpperCase())}</div><div class="hp">${E(pp.probabilita)}%<span>affidabilità</span></div><p>${E(clean(pp.motivazione_breve))}</p></div>` : ''}
${m.prob_1x2 ? `<div class="box"><h3>Probabilità</h3>${bar([{ l: '1', v: k['1'], c: '#10B981' }, { l: 'X', v: k.X, c: '#64748B' }, { l: '2', v: k['2'], c: '#06B6D4' }])}${bar([{ l: 'Under 2.5', v: k['U2.5'], c: '#8B5CF6' }, { l: 'Over 2.5', v: k['O2.5'], c: '#F59E0B' }])}${bar([{ l: 'Gol', v: k.GG, c: '#10B981' }, { l: 'NoGol', v: k.NG, c: '#EF4444' }])}<p class="mu" style="font-size:12px">Affidabilità statistica: <b style="color:var(--go)">${E(m.affidabilita ?? '-')}%</b></p></div>
<div class="box"><h3>Analisi tattica</h3><p style="font-size:14px">${E(clean(m.analisi))}</p></div>
<div class="box"><h3>Probabili formazioni</h3>${['casa', 'trasferta'].map(s => f[s] ? `<p style="font-size:13px;margin-bottom:8px"><b>${E(s === 'casa' ? m.casa : m.trasf)}</b> (${E(f[s].modulo)}): ${E((f[s].undici || []).join(', '))}</p>` : '').join('')}</div>
<div class="box"><h3>Possibili marcatori</h3>${pl(m.possibili_marcatori) || '<p class="mu">–</p>'}</div>
<div class="box"><h3>Rischio cartellino</h3>${pl(m.possibili_ammoniti, 1) || '<p class="mu">–</p>'}</div>
<div class="box"><h3>Tutti i mercati</h3><div class="g">${Object.entries(k).map(([x, v]) => `<span>${E(lbl(x))}<b>${E(v)}%</b></span>`).join('')}</div></div>` : '<p class="empty">Analisi non ancora disponibile.</p>'}${disc()}`;
  openId = m.id; $('#sheet').scrollTop = 0; $('#sheet').classList.add('open'); $('#scrim').classList.add('open');
}

/* ---------- Azioni & Aggiornamento Live ---------- */
const A = {
  tab(v) { tab = v; render(); scrollTo(0, 0) },
  comp(v) { F.c = v; F.f = false; render() },
  favf() { F.f = !F.f; if (F.f) F.c = ''; render() },
  open(v) { const m = D.find(x => x.id == v); if (m) sheet(m) },
  close() { openId = null; $('#sheet').classList.remove('open'); $('#scrim').classList.remove('open') },
  fav(v) { v = +v; fav = fav.includes(v) ? fav.filter(x => x != v) : [...fav, v]; L.fav = JSON.stringify(fav); if (F.f) return render(); document.querySelectorAll(`[data-a=fav][data-v="${v}"]`).forEach(b => b.classList.toggle('on', fav.includes(v))); const n = $('#nf'); if (n) n.textContent = fav.length },
  theme() { const d = document.documentElement, t = d.dataset.theme === 'dark' ? 'light' : 'dark'; d.dataset.theme = t; L.theme = t; $('#th').innerHTML = ic(t === 'dark' ? 'sun' : 'moon'); document.querySelector('meta[name=theme-color]').content = t === 'dark' ? '#0B1120' : '#F1F5FB' },
  share() { share('352 Pronostici - Analisi & Statistiche Calcio', location.href.split('#')[0]) },
  enter() { L.ok18 = 1; $('#welcome').classList.remove('open') },
  best() { G.best = !G.best; render() }, risk(v) { G.risk = v; render() },
  mkt(v) { G.m = G.m.includes(v) ? G.m.filter(x => x != v) : [...G.m, v]; render() },
  gen() { genera(); render() },
  async cp() { const ok = await share(gtext()); if (ok) { const b = $('#cpb'); if (b) { b.classList.add('ok'); b.innerHTML = ic('check') + 'Copiato!'; setTimeout(() => { b.classList.remove('ok'); b.innerHTML = ic('copy') + 'Copia / Condividi combinazione' }, 1800) } } },
  async refresh() {
    toast('Aggiornamento dati in corso...');
    try {
      const r = await fetch('data/matches.json?t=' + Date.now(), { cache: 'no-store' });
      const j = await r.json();
      D = j.matches || [];
      meta = j.aggiornato_il || '';
      render();
      toast('Dati live aggiornati');
    } catch {
      toast('Aggiornamento non riuscito');
    }
  },
  ev(v) {
    const m = D.find(x => x.id == v);
    if (!m) return;
    if (TL[v]) { delete TL[v]; $('#tl' + v).innerHTML = ''; return; }
    const evs = m.eventi || [];
    const marc = (m.possibili_marcatori || []).map(p => `⚽ ${E(p.giocatore)} (${p.prob}%)`);
    TL[v] = evs.length
      ? `<div class="tl">${evs.map(x => `<div><b>${E(x.min)}'</b> ${E(x.t)}</div>`).join('')}</div>`
      : (marc.length ? `<div class="tl"><div style="color:var(--mu);font-size:12px">Giocatori chiave: ${marc.join(' · ')}</div></div>` : '<p class="mu" style="font-size:13px;margin-top:8px">Nessun evento registrato al momento.</p>');
    $('#tl' + v).innerHTML = TL[v];
  }
};

document.addEventListener('click', e => { const b = e.target.closest('[data-a]'); if (b && A[b.dataset.a]) A[b.dataset.a](b.dataset.v) });
document.addEventListener('change', e => { if (e.target.dataset.s === 'n') G.n = +e.target.value });
document.addEventListener('keydown', e => { if (e.key === 'Escape') A.close() });

/* ---------- Avvio ---------- */
const th = L.theme || 'dark'; document.documentElement.dataset.theme = th; $('#th').innerHTML = ic(th === 'dark' ? 'sun' : 'moon');
if (!L.ok18) $('#welcome').classList.add('open');
$('#view').innerHTML = skeleton(); stats();
fetch('data/matches.json', { cache: 'no-store' }).then(r => r.json()).then(j => { D = j.matches || []; meta = j.aggiornato_il || ''; render() }).catch(() => { $('#view').innerHTML = '<p class="empty">Dati non disponibili. Riprova più tardi.</p>' });
if ('serviceWorker' in navigator) navigator.serviceWorker.register('service-worker.js').catch(() => { });
