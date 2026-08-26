# HostPro on the web — setup

The app is served from your own domain instead of from inside the Apps Script
sandbox. Apps Script keeps doing everything else — schema, auth, Slack
ingestion, the API. `Code.gs` and `slack.gs` are not modified.

What you get: a real installable app on iPhone and Android from one link, a
`git push` deploy instead of Manage deployments, an offline shell, and one push
notification mechanism covering both platforms later.

---

## What is in this folder

| Path | What it is |
|---|---|
| `setup.py` | Patches your `Index.html` and puts it in `public/`. Run this first |
| `public/manifest.webmanifest` | Makes it installable. Named **HostPro**, black theme |
| `public/sw.js` | Offline shell and push handlers. `Index.html` already registers it |
| `public/offline.html` | Shown when there is no network and no cached shell |
| `public/icon-*.png` | Your logo at 180, 192, 512 and maskable 512 |
| `public/_headers` | Cloudflare caching rules |
| `functions/api/exec.js` | The proxy. This is what removes the CORS problem |

---

## Step 1 — patch your Index.html

Copy `Index.html` out of Apps Script into a file, then from inside this folder:

```bash
python3 setup.py Index.html
```

It prints what it changed and writes `public/index.html`. Your original is not
touched. Re-run it any time you change the app in Apps Script.

**Exactly one line changes.** Your `Index.html` already has the manifest link,
the apple-touch-icon, `apple-mobile-web-app-capable`, `viewport-fit=cover`, and
the service worker registration. All that was missing is where the app sends its
API calls. After the patch:

- **Served by Apps Script** — unchanged. `google.script.run` handles everything
  and the proxy is never used, so `/exec` stays a working backup.
- **The Android APK** — unchanged. Capacitor is detected and goes straight to
  Apps Script natively, as it does today.
- **Cloudflare, iPhone, laptop** — calls go to `/api/exec` on the same origin.

## Step 2 — push to GitHub

New private repo, or a folder inside `ghulamghoas1773-oss/hostpro-os`.

```bash
git init
git add .
git commit -m "HostPro web app"
git remote add origin git@github.com:ghulamghoas1773-oss/hostpro-web.git
git push -u origin main
```

Or use github.com ▸ new repository ▸ **uploading an existing file** and drag the
folder contents in.

## Step 3 — connect Cloudflare Pages

dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Connect
to Git** → pick the repo.

| Setting | Value |
|---|---|
| Framework preset | None |
| Build command | *(leave empty)* |
| Build output directory | `public` |

Deploy. You get a `.pages.dev` link in about a minute. The `functions/` folder
at the repo root is picked up automatically — a Pages convention, not something
you configure.

## Step 4 — check the proxy before anything else

Open your `.pages.dev` link with `/api/exec?ping=1` on the end. You should see:

```json
{"ok":true,"v":"2.0"}
```

That single response proves the whole chain: Cloudflare reached Apps Script,
Apps Script ran, and JSON came back. If you instead get an error object, its
`error` field names the fix — usually **Deploy ▸ Manage deployments ▸ Who has
access ▸ Anyone**.

Then open the plain link and sign in. Everyone signs in once on the new domain,
because a browser session does not cross origins. After that it persists exactly
as it does now.

## Step 5 — your own domain

Pages project → **Custom domains** → **Set up a domain** → e.g.
`os.hostpro.agency`. If `hostpro.agency` already uses Cloudflare for DNS the
record is created for you; otherwise add the CNAME Cloudflare shows you at your
registrar. TLS is automatic.

Do this **before** sending the link out. Moving domains later means everyone
signs in again and re-adds the home screen icon.

---

## One thing to know about "Change workspace link"

Settings has a **Change workspace link** button, and the sign-in screen has one
too. On the web version, using it stores an override in `localStorage` that
takes priority over the proxy. It still works — your app sends `text/plain`,
which avoids a CORS preflight — but it is the flakier path and there is no
reason to reach for it.

If someone does it by accident and the app stops loading, the fix is Settings ▸
Change workspace link ▸ clear the box, or clear site data. Tell me if you would
rather I hide that button on the web build.

---

## Cost

Cloudflare Pages free tier: unlimited static requests, 500 builds a month,
100,000 function calls a day. Your team will not approach that.

Workers charge CPU time, not wall-clock. Waiting 5–15 seconds for Apps Script is
I/O, so it costs essentially nothing. This is why not Vercel: its free tier
times functions out at 10 seconds by default and its terms cover personal,
non-commercial use only.

---

## Push notifications, when you get to them

`sw.js` already handles `push` and `notificationclick`. Three pieces remain:

1. **VAPID keys** — `npx web-push generate-vapid-keys`. Public key in the
   client, private key as a Cloudflare secret.
2. **Subscribe** — after sign-in, request permission from a real tap, call
   `registration.pushManager.subscribe()`, and POST the subscription to Apps
   Script to store against the person's row in `People`.
3. **Send** — a Pages Function that signs a VAPID request, called from an Apps
   Script trigger when an issue passes 24 hours unanswered. You already compute
   that number on the dashboard.

On iPhone this only works after the app is on the home screen, and permission
must be requested from a tap inside the installed app. Android has neither
restriction.

---

## Rolling back

Cloudflare keeps every deployment. Pages project → **Deployments** → pick an
earlier one → **Rollback**. Seconds.

And `/exec` still serves the app directly, so it remains a live fallback.
