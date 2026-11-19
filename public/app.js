"use strict";
const FILTRI = [["ALL","Tutte"],["SA","Serie A"],["PL","Premier"],["PD","Liga"],["BL1","Bundesliga"],["FL1","Ligue 1"],["CL","Champions"]];
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const HEX = /^#[0-9a-f]{6}$/i;
let dati = null, filtro = "ALL", aperta = null, lato = "casa", ultimoFocus = null;

/* ---------- colori e scudetti generati (nessun logo ufficiale) ---------- */
const hsl = (nome, l) => { let h = 0; for (const c of nome) h = (h * 31 + c.charCodeAt(0)) % 360; return `hsl(${h} 55% ${l}%)`; };
const colori = (sq) => { const c = sq.colori || []; return [HEX.test(c[0]) ? c[0] : hsl(sq.nome, 32), HEX.test(c[1]) ? c[1] : hsl(sq.nome + "x", 75)]; };
function lum(c) {
  if (!HEX.test(c)) return 0.2;
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16) / 255).map((v) => v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const inchiostro = (bg) => lum(bg) > 0.4 ? "#10252B" : "#fff";
function scudetto(sq, w = 40) {
  const [a, b] = colori(sq), id = "c" + Math.random().toString(36).slice(2, 8);
  const forma = "M3 3h34v21c0 10-8 16-17 20C11 40 3 34 3 24z";
  return `<svg class="crest" width="${w}" height="${Math.round(w * 1.15)}" viewBox="0 0 40 46" role="img" aria-label="Scudetto ${esc(sq.nome)}"><defs><clipPath id="${id}"><path d="${forma}"/></clipPath></defs><g clip-path="url(#${id})"><rect width="40" height="46" fill="${a}"/><rect y="29" width="40" height="18" fill="${b}"/></g><path d="${forma}" fill="none" stroke="#10252B" stroke-opacity=".55" stroke-width="1.6"/><text x="20" y="21" text-anchor="middle" font-size="12" font-weight="800" fill="${inchiostro(a)}" font-family="system-ui,sans-serif">${esc(sq.sigla)}</text></svg>`;
}

/* ---------- campo con formazione ---------- */
const cognome = (n) => String(n).trim().split(/\s+/).slice(-1)[0].slice(0, 11);
function campo(f, sq) {
  const [a, b] = colori(sq);
  const nums = String(f?.modulo || "").split("-").map(Number);
  const ok = f && Array.isArray(f.giocatori) && f.giocatori.length === 11 && nums.length >= 2 && nums.every((n) => n > 0) && nums.reduce((x, y) => x + y, 0) === 10;
  let giocatori = "";
  if (ok) {
    const righe = [[f.giocatori[0]]]; let i = 1;
    for (const n of nums) { righe.push(f.giocatori.slice(i, i + n)); i += n; }
    const tot = righe.length - 1;
    righe.forEach((r, k) => {
      const y = k === 0 ? 116 : 96 - (k - 1) * (84 / (tot - 1));
      r.forEach((nome, j) => {
        const x = ((j + 1) * 100) / (r.length + 1);
        giocatori += `<circle cx="${x}" cy="${y}" r="5" fill="${a}" stroke="${b}" stroke-width="1.6"/><text class="pn" x="${x}" y="${y + 9.5}" text-anchor="middle">${esc(cognome(nome))}</text>`;
      });
    });
  }
  const strisce = [0, 1, 2, 3, 4, 5].map((i) => `<rect x="0" y="${i * 21.7}" width="100" height="10.85" fill="#fff" opacity=".05"/>`).join("");
  return `<svg class="campo" viewBox="0 0 100 130" role="img" aria-label="Formazione ${esc(sq.nome)}, modulo ${esc(f?.modulo)}"><rect width="100" height="130" fill="#2F7D4F"/>${strisce}<g stroke="#fff" stroke-opacity=".75" fill="none" stroke-width=".7"><rect x="4" y="4" width="92" height="122"/><line x1="4" y1="65" x2="96" y2="65"/><circle cx="50" cy="65" r="9"/><rect x="24" y="4" width="52" height="18"/><rect x="24" y="108" width="52" height="18"/><rect x="38" y="4" width="24" height="7"/><rect x="38" y="119" width="24" height="7"/></g>${giocatori}${ok ? "" : '<text x="50" y="65" text-anchor="middle" font-size="5" fill="#fff">Formazione non disponibile</text>'}</svg>`;
}

/* ---------- barre ---------- */
const seg = (v, cls) => `<span class="${cls}" style="flex:${Math.max(v, 3)}">${v}%</span>`;
const duo = (a, b, la, lb) => `<div class="blocco"><div class="lbl"><span>${la}</span><span>${lb}</span></div><div class="bar">${seg(a, "sa")}${seg(b, "sb")}</div></div>`;

/* ---------- lista (raggruppata per giorno) ---------- */
const ora = (iso) => new Date(iso).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
const chiaveGiorno = (iso) => new Date(iso).toLocaleDateString("en-CA");
const giorno = (iso) => new Date(iso).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" }).replace(/(^|\s)\S/g, (c) => c.toUpperCase());
function renderFiltri() {
  $("#filtri").innerHTML = FILTRI.map(([c, n]) => `<button class="chip" data-f="${c}" aria-pressed="${c === filtro}">${n}</button>`).join("");
}
function cardHtml(p) {
  const pr = p.analisi?.probabilita_1x2;
  return `<button class="card" data-id="${p.id}"><div class="meta"><span>${esc(p.competizione.nome)}</span><span>${p.giornata ? "Giornata " + p.giornata : ""}</span></div><div class="sfida"><div class="sq">${scudetto(p.squadra_casa)}${esc(p.squadra_casa.nome)}</div><div class="ora">${ora(p.ora_utc)}</div><div class="sq">${scudetto(p.squadra_trasferta)}${esc(p.squadra_trasferta.nome)}</div></div>${pr ? `<div class="bar" aria-hidden="true">${seg(pr["1"], "s1")}${seg(pr.X, "sX")}${seg(pr["2"], "s2")}</div>` : ""}</button>`;
}
function renderLista() {
  const tutte = [...(dati.partite || [])].sort((a, b) => a.ora_utc.localeCompare(b.ora_utc));
  const sel = filtro === "ALL" ? tutte : tutte.filter((p) => p.competizione.codice === filtro);
  let html = dati.esempio ? '<div class="banner">Dati di esempio con squadre inventate. Le partite reali compaiono dopo il primo avvio del workflow.</div>' : "";
  let corrente = "";
  for (const p of sel) {
    const k = chiaveGiorno(p.ora_utc);
    if (k !== corrente) { corrente = k; html += `<h2 class="giorno">${giorno(p.ora_utc)}</h2>`; }
    html += cardHtml(p);
  }
  if (!sel.length) html += '<div class="vuoto">Nessuna partita nei prossimi 7 giorni per questa competizione.</div>';
  $("#lista").innerHTML = html;
}

/* ---------- scheda partita ---------- */
const pos = (sq) => sq.classifica ? `<span class="pos">${sq.classifica.posizione}° · ${sq.classifica.punti} pt</span>` : "";
function renderScheda() {
  const p = aperta, a = p.analisi, c = p.squadra_casa, t = p.squadra_trasferta;
  let h = `<div class="testata"><div class="sub">${esc(p.competizione.nome)} · ${giorno(p.ora_utc)} - ${ora(p.ora_utc)}</div><div class="sfida"><div class="sq">${scudetto(c, 52)}${esc(c.nome)}${pos(c)}</div><div class="ora">vs</div><div class="sq">${scudetto(t, 52)}${esc(t.nome)}${pos(t)}</div></div></div>`;
  if (!a) return h + '<p class="vuoto">Analisi non disponibile per questa partita.</p>' + nota();
  const o = a.probabilita_1x2, g = a.probabilita_gol, casa = lato === "casa";
  h += `<h2>Probabilità dell'esito</h2><div class="blocco"><div class="lbl"><span>${esc(c.nome)}</span><span>Pareggio</span><span>${esc(t.nome)}</span></div><div class="bar">${seg(o["1"], "s1")}${seg(o.X, "sX")}${seg(o["2"], "s2")}</div></div>`;
  h += `<h2>Gol</h2>${duo(g.over_2_5, g.under_2_5, "Over 2.5", "Under 2.5")}${duo(g.gol, g.nogol, "Gol", "NoGol")}`;
  h += `<h2>Probabili formazioni</h2><div class="tabs"><button class="tab" data-lato="casa" aria-pressed="${casa}">${esc(c.nome)}</button><button class="tab" data-lato="trasferta" aria-pressed="${!casa}">${esc(t.nome)}</button></div>`;
  h += casa ? campo(a.probabile_formazione_casa, c) : campo(a.probabile_formazione_trasferta, t);
  h += `<p class="sub">Modulo ${esc((casa ? a.probabile_formazione_casa : a.probabile_formazione_trasferta).modulo)} · formazione stimata</p>`;
  h += `<h2>Analisi tattica</h2><p class="testo">${esc(a.analisi_tattica)}</p><h2>Consiglio tecnico</h2><p class="testo">${esc(a.consiglio_tecnico)}</p>`;
  return h + nota();
}
const nota = () => '<p class="nota">Stime generate da un modello di intelligenza artificiale: possono contenere errori. Solo scopo informativo e statistico. Vietato ai minori di 18 anni.</p>';
function apri(id) {
  aperta = dati.partite.find((p) => String(p.id) === String(id)); if (!aperta) return;
  lato = "casa"; ultimoFocus = document.activeElement;
  $("#scheda").innerHTML = renderScheda(); $("#sheet").hidden = false;
  document.body.style.overflow = "hidden"; $("#chiudi").focus();
}
function chiudi() { $("#sheet").hidden = true; document.body.style.overflow = ""; ultimoFocus?.focus(); }

document.addEventListener("click", (e) => {
  const f = e.target.closest("[data-f]"), card = e.target.closest("[data-id]"), tab = e.target.closest("[data-lato]");
  if (f) { filtro = f.dataset.f; renderFiltri(); renderLista(); }
  else if (card) apri(card.dataset.id);
  else if (tab) { lato = tab.dataset.lato; $("#scheda").innerHTML = renderScheda(); }
  else if (e.target.id === "chiudi" || e.target.id === "sheet") chiudi();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#sheet").hidden) chiudi(); });

/* ---------- avvio ---------- */
(async function () {
  renderFiltri();
  try {
    const r = await fetch("data/matches.json", { cache: "no-cache" });
    if (!r.ok) throw new Error(r.status);
    dati = await r.json();
    $("#sottotitolo").textContent = "Partite dei prossimi 7 giorni";
    renderLista();
  } catch (e) {
    $("#sottotitolo").textContent = "Dati non disponibili";
    $("#lista").innerHTML = '<div class="vuoto">Impossibile caricare le partite. Controlla la connessione e riprova.</div>';
  }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("service-worker.js").catch(() => {});
})();
