
const CACHE_NAME = "pronostici352-v1";

const SHELL = [
    "./",
    "index.html",
    "style.css",
    "app.js",
    "manifest.json"
];

// INSTALLAZIONE
self.addEventListener("install", (event) => {

    event.waitUntil(

        caches.open(CACHE_NAME)

            .then((cache) => cache.addAll(SHELL))

            .then(() => self.skipWaiting())

    );

});


// ATTIVAZIONE E PULIZIA CACHE VECCHIE
self.addEventListener("activate", (event) => {

    event.waitUntil(

        caches.keys()

            .then((keys) =>

                Promise.all(

                    keys

                        .filter((key) => key !== CACHE_NAME)

                        .map((key) => caches.delete(key))

                )

            )

            .then(() => self.clients.claim())

    );

});


// GESTIONE RICHIESTE
self.addEventListener("fetch", (event) => {

    const request = event.request;

    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);

    if (url.origin !== self.location.origin) {
        return;
    }


    // DATI PARTITE:
    // Rete prioritaria per ottenere risultati e marcatori aggiornati.
    // Cache utilizzata esclusivamente come fallback offline.

    if (url.pathname.includes("/data/matches.json")) {

        event.respondWith(

            fetch(request)

                .then((response) => {

                    if (response.ok) {

                        const copia = response.clone();

                        caches.open(CACHE_NAME)

                            .then((cache) => {

                                cache.put(request, copia);

                            });

                    }

                    return response;

                })

                .catch(() => {

                    return caches.match(request);

                })

        );

        return;

    }


    // FILE STATICI:
    // Cache first, rete come fallback.

    event.respondWith(

        caches.match(request)

            .then((cached) => {

                if (cached) {
                    return cached;
                }

                return fetch(request).then((response) => {

                    if (response.ok) {

                        const copia = response.clone();

                        caches.open(CACHE_NAME)

                            .then((cache) => {

                                cache.put(request, copia);

                            });

                    }

                    return response;

                });

            })

    );

});
