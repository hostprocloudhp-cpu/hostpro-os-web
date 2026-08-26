# Three edits to `Index.html`

Copy your existing `Index.html` into `public/index.html`, then make these three
changes. Nothing else in the file moves. The same patched file still works when
served by Apps Script, so the `/exec` URL stays alive as a backup.

---

## 1. Point the API at the proxy

Find `BAKED_URL` near the top of the inline script:

```js
const BAKED_URL = "https://script.google.com/macros/s/AKfycby.../exec";
```

Change it to a relative path:

```js
const BAKED_URL = "/api/exec";
```

That single change is what removes the CORS problem. `/api/exec` is the same
origin as the app, so the browser treats it as an ordinary request.

**If you want one file that works on both hosts**, use this instead. It keeps
Apps Script working when the file is served from `script.google.com`, and uses
the proxy everywhere else:

```js
const BAKED_URL = location.hostname.indexOf("google.com") > -1
  ? "https://script.google.com/macros/s/AKfycbyC_sOt3Btj-8vnNIT2X_nTqUbm6x0QVkVC8t3GmwHdeOmrZOv8SBDdI03fpyDLklIJsg/exec"
  : "/api/exec";
```

Written with `indexOf` rather than a regex on purpose — a regex here is exactly
the shape that broke the page before.

---

## 2. Add the install metadata to `<head>`

Paste this block inside `<head>`, just before `</head>`:

```html
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#000000">
<link rel="apple-touch-icon" href="/icons/icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<meta name="apple-mobile-web-app-title" content="HostPro OS">
```

Also check the viewport tag already in the file. It needs `viewport-fit=cover`
so the app fills the screen on notched iPhones:

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

`apple-mobile-web-app-title` is what appears under the icon on the home screen.
Without it iOS uses the `<title>`, which is usually too long and gets truncated.

---

## 3. Register the service worker

Paste this at the very **end** of the existing inline `<script>` block, after
your last line of code and before `</script>`. Keep it in the same block — do
not add a second `<script>` tag.

```js
if ("serviceWorker" in navigator && location.protocol === "https:") {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").then(function (reg) {
      reg.addEventListener("updatefound", function () {
        var incoming = reg.installing;
        if (!incoming) return;
        incoming.addEventListener("statechange", function () {
          if (incoming.state === "installed" && navigator.serviceWorker.controller) {
            showUpdateBar();
          }
        });
      });
    }).catch(function (err) {
      console.warn("[pwa] service worker not registered:", err);
    });
  });
}

function showUpdateBar() {
  if (document.getElementById("hp-update-bar")) return;
  var bar = document.createElement("div");
  bar.id = "hp-update-bar";
  bar.style.cssText =
    "position:fixed;left:12px;right:12px;bottom:12px;z-index:99999;" +
    "display:flex;align-items:center;gap:12px;padding:13px 16px;" +
    "background:rgba(13,13,13,.95);border:1px solid rgba(255,255,255,.08);" +
    "border-radius:18px;color:#cccccc;font-size:14px;" +
    "box-shadow:0 12px 40px rgba(0,0,0,.6)";
  var msg = document.createElement("span");
  msg.textContent = "A new version is ready.";
  msg.style.flex = "1";
  var btn = document.createElement("button");
  btn.textContent = "Reload";
  btn.style.cssText =
    "padding:8px 16px;border:0;border-radius:8px;background:#81dae2;" +
    "color:#04191b;font-weight:700;font-size:13.5px;cursor:pointer";
  btn.onclick = function () { location.reload(); };
  bar.appendChild(msg);
  bar.appendChild(btn);
  document.body.appendChild(bar);
}
```

The `location.protocol === "https:"` guard means this stays quiet when the file
is served from inside the Apps Script sandbox, where registration would fail
anyway.

---

## Before you paste anything back into Apps Script

`python3 check.py public/index.html`

The `//`-in-regex trap only exists in how Apps Script serves the page, so it
stops mattering for the Cloudflare copy. But you are keeping `/exec` alive as a
backup, which means the same file still gets pasted into Apps Script sometimes.
Keep running the guard for as long as that is true.
