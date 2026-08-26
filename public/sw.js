/**
 * HostPro — service worker
 *
 * Index.html already registers this, and already skips registering it inside
 * Apps Script and inside the Capacitor shell. Nothing to wire up.
 *
 * Strategy, deliberately conservative:
 *   /api/*        network only, never cached. The app has its own offline
 *                 handling: it draws hostpro_cache from localStorage and then
 *                 fetches live. Caching API responses here would fight that.
 *   navigations   network first, cache as fallback. A deploy shows up on the
 *                 next open; offline still opens the app shell.
 *   everything    stale-while-revalidate.
 *   else
 *
 * Bump CACHE_VERSION whenever this file or the shell list changes.
 */

const CACHE_VERSION = "hostpro-v1";
const SHELL = [
  "/",
  "/index.html",
  "/offline.html",
  "/manifest.webmanifest",
  "/icon-180.png",
  "/icon-192.png",
  "/icon-512.png",
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(function (cache) {
      // addAll fails the whole install if one file 404s, which hides the
      // problem. Add individually so a missing icon cannot break the app.
      return Promise.all(
        SHELL.map(function (url) {
          return cache.add(url).catch(function (err) {
            console.warn("[sw] could not cache", url, err);
          });
        })
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches
      .keys()
      .then(function (keys) {
        return Promise.all(
          keys
            .filter(function (key) { return key !== CACHE_VERSION; })
            .map(function (key) { return caches.delete(key); })
        );
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Live data only. Never serve a stale issue list or a stale balance.
  if (url.pathname.indexOf("/api/") === 0) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(function (response) {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then(function (cache) {
            cache.put("/index.html", copy);
          });
          return response;
        })
        .catch(function () {
          return caches.match("/index.html").then(function (cached) {
            return cached || caches.match("/offline.html");
          });
        })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(function (cached) {
      const network = fetch(request)
        .then(function (response) {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_VERSION).then(function (cache) {
              cache.put(request, copy);
            });
          }
          return response;
        })
        .catch(function () { return cached; });
      return cached || network;
    })
  );
});

/* ------------------------------------------------------------------ */
/* Push. Inert until VAPID keys and a sender exist — see DEPLOY.md.     */
/* Works on Android now, and on iPhone once the app is installed to the */
/* home screen. One implementation covers both.                        */
/* ------------------------------------------------------------------ */

self.addEventListener("push", function (event) {
  let payload = {};
  try { payload = event.data ? event.data.json() : {}; }
  catch (err) { payload = { body: event.data ? event.data.text() : "" }; }

  event.waitUntil(
    self.registration.showNotification(payload.title || "HostPro", {
      body: payload.body || "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      tag: payload.tag || "hostpro",
      data: { url: payload.url || "/" },
    })
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then(function (list) {
        for (let i = 0; i < list.length; i++) {
          if ("focus" in list[i]) {
            list[i].navigate(target);
            return list[i].focus();
          }
        }
        return self.clients.openWindow(target);
      })
  );
});
