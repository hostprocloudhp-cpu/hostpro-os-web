/**
 * HostPro — API proxy
 *
 * Makes the Apps Script backend look like it lives on the same origin as the
 * app. Same origin means the browser never treats these as cross-origin
 * requests: no CORS preflight, no OPTIONS that Apps Script cannot answer, no
 * redirect quietly dropping a POST body.
 *
 * Nothing in Code.gs changes. doPost already reads e.postData.contents and
 * JSON-parses it, which is exactly what this forwards.
 *
 * Optional: set APPS_SCRIPT_URL in the Cloudflare dashboard under
 * Settings > Variables and Secrets to move the link out of the repo. The
 * fallback below is your current live deployment, so it works untouched.
 */

const FALLBACK_URL =
  "https://script.google.com/macros/s/AKfycbyC_sOt3Btj-8vnNIT2X_nTqUbm6x0QVkVC8t3GmwHdeOmrZOv8SBDdI03fpyDLklIJsg/exec";

export async function onRequest(context) {
  const { request, env } = context;
  const upstreamBase = env.APPS_SCRIPT_URL || FALLBACK_URL;
  const incoming = new URL(request.url);
  const target = upstreamBase + incoming.search;

  const init = {
    method: request.method,
    // Apps Script answers a POST with a 302 to googleusercontent. Following it
    // as a GET is correct: the POST has already run, and the redirect target
    // serves its result.
    redirect: "follow",
    headers: {},
  };

  if (request.method === "POST" || request.method === "PUT") {
    init.body = await request.text();
    init.headers["Content-Type"] = "text/plain;charset=utf-8";
  }

  let upstream;
  try {
    upstream = await fetch(target, init);
  } catch (err) {
    return jsonOut(
      {
        ok: false,
        error:
          "The proxy could not reach Apps Script. Check that the /exec deployment is live. Detail: " +
          String(err),
      },
      502
    );
  }

  const body = await upstream.text();
  const contentType = upstream.headers.get("content-type") || "";

  if (!upstream.ok) {
    return jsonOut(
      {
        ok: false,
        error:
          upstream.status === 401 || upstream.status === 403
            ? "Apps Script refused the request. In Deploy \u203a Manage deployments, set Who has access to Anyone."
            : "Apps Script returned " + upstream.status + ". " + body.slice(0, 300),
      },
      502
    );
  }

  // A web page instead of JSON usually means the deployment needs a new
  // version, or the script threw before it could respond. Say that plainly
  // rather than letting JSON.parse fail somewhere inside the app.
  if (contentType.indexOf("text/html") > -1 && body.trimStart().charAt(0) === "<") {
    return jsonOut(
      {
        ok: false,
        error:
          "Apps Script returned a web page instead of data. Redeploy: Deploy \u203a Manage deployments \u203a pencil \u203a New version.",
      },
      502
    );
  }

  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": contentType || "application/json;charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

function jsonOut(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status,
    headers: {
      "Content-Type": "application/json;charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
