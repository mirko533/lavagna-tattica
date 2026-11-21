const CACHE_NAME = "pronostici352-v9";
const SHELL = ["./", "index.html", "style.css", "app.js", "manifest.json", "icons/icon-192.png", "icons/icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== CACHE_NAME).map(x => caches.delete(x)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.endsWith("/data/matches.json") || url.pathname.endsWith("/data/squads_cache.json")) {
    // Network First con cache: "no-store"; la cache serve solo se si e' offline
    e.respondWith(fetch(req, { cache: "no-store" }).then(r => {
      const copy = r.clone();
      caches.open(CACHE_NAME).then(c => c.put(url.origin + url.pathname, copy));
      return r;
    }).catch(() => caches.match(url.origin + url.pathname)));
    return;
  }
  e.respondWith(caches.match(req).then(hit => {
    const net = fetch(req).then(r => {
      const copy = r.clone();
      caches.open(CACHE_NAME).then(c => c.put(req, copy));
      return r;
    }).catch(() => hit);
    return hit || net;
  }));
});
