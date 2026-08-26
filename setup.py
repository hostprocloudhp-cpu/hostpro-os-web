#!/usr/bin/env python3
"""
HostPro — one-step setup.

Takes your Index.html exactly as it is in Apps Script, applies the one change
it needs to run on a real web host, and writes it to public/index.html.

    python3 setup.py Index.html

You do not edit anything by hand. Run it again any time you change the file in
Apps Script — it is safe to re-run and it never touches your original.
"""

import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "public", "index.html")

GS_URL = ("https://script.google.com/macros/s/"
          "AKfycbyC_sOt3Btj-8vnNIT2X_nTqUbm6x0QVkVC8t3GmwHdeOmrZOv8SBDdI03fpyDLklIJsg/exec")

# Written without a regex on purpose. A regex whose source contains two
# consecutive forward slashes is what broke this page three times before;
# there is no reason to reintroduce the shape.
NEW_BAKED = (
    "const GS_EXEC_URL = '" + GS_URL + "';\n"
    "/* Where the app sends its API calls.\n"
    "   Installed Android shell -> straight to Apps Script, because Capacitor\n"
    "     makes the request natively and there is no origin to share.\n"
    "   Anywhere else (Cloudflare, a laptop, an iPhone home screen) -> the\n"
    "     same-origin proxy at /api/exec, so no CORS question ever arises.\n"
    "   Served by Apps Script itself -> neither is used; google.script.run\n"
    "     takes over and API_URL is ignored. */\n"
    "const IS_NATIVE_SHELL = !!(window.Capacitor && window.Capacitor.isNativePlatform\n"
    "  && window.Capacitor.isNativePlatform());\n"
    "const BAKED_URL = IS_NATIVE_SHELL ? GS_EXEC_URL : '/api/exec';"
)


def fail(msg):
    print("\n  STOPPED: " + msg + "\n")
    sys.exit(1)


def patch_baked_url(src):
    """Replace the single BAKED_URL declaration line."""
    marker = "const BAKED_URL"
    at = src.find(marker)
    if at == -1:
        fail("Could not find the BAKED_URL line in that file. Is this the right "
             "Index.html? Nothing was written.")
    if src.find(marker, at + 1) != -1:
        fail("Found BAKED_URL more than once. That is unexpected — send the file "
             "back rather than guessing. Nothing was written.")
    end = src.find(";", at)
    if end == -1:
        fail("The BAKED_URL line has no semicolon. Nothing was written.")
    return src[:at] + NEW_BAKED + src[end + 1:], True


def patch_app_title(src):
    """iOS shows this under the home screen icon. Match the chosen app name."""
    old = '<meta name="apple-mobile-web-app-title" content="HostPro OS">'
    new = '<meta name="apple-mobile-web-app-title" content="HostPro">'
    if old in src:
        return src.replace(old, new), True
    return src, False


def guard(src):
    """
    The invariants Apps Script actually cares about. Worth checking even here,
    because /exec stays alive as a backup and this file still gets pasted back.
    """
    problems = []
    for m in re.finditer(r"/[^/\n*][^\n]*?/[gimsuy]*", src):
        if "//" in m.group(0):
            problems.append("a regex containing // : " + m.group(0)[:60])
    if src.count("<script") - src.count("<script src") > 1:
        problems.append("more than one inline <script> block")
    if "<?" in src:
        problems.append("an Apps Script scriptlet <?")
    return problems


def main():
    if len(sys.argv) < 2:
        fail("Tell me where your Index.html is.\n"
             "           python3 setup.py Index.html")

    path = sys.argv[1]
    if not os.path.isfile(path):
        fail("No file at: " + path)

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        src = fh.read()

    if "hostpro" not in src.lower():
        fail("That file does not look like the HostPro app. Nothing was written.")

    print("\nHostPro web setup")
    print("  read   " + path + "  (" + str(round(len(src) / 1024)) + " KB)")

    src, _ = patch_baked_url(src)
    print("  patch  API calls now go to /api/exec (Android shell unchanged)")

    src, did = patch_app_title(src)
    if did:
        print("  patch  home screen name set to HostPro")

    problems = guard(src)
    if problems:
        print("\n  Heads up, these would break the Apps Script copy:")
        for p in problems:
            print("    - " + p)
        print("  The Cloudflare copy is unaffected.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        shutil.copyfile(OUT, OUT + ".previous")
        print("  keep   previous version saved as index.html.previous")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(src)

    print("  wrote  public/index.html")

    missing = [f for f in ["manifest.webmanifest", "sw.js", "offline.html",
                           "icon-180.png", "icon-192.png", "icon-512.png",
                           "icon-maskable-512.png"]
               if not os.path.exists(os.path.join(HERE, "public", f))]
    if missing:
        print("\n  Missing from public/: " + ", ".join(missing))
    else:
        print("\nReady. Next: push this folder to GitHub, then connect Cloudflare")
        print("Pages with build output directory set to  public")
    print("")


if __name__ == "__main__":
    main()
