"""
Stage 1 of the research pipeline: fetch real developer documentation.

For every app it tries a list of candidate documentation URLs, follows redirects,
and saves the *rendered HTML converted to plain text* to data/sources/<id>.txt.
Nothing here invents content: if a page cannot be fetched, the manifest records
the failure and the app has no source text to extract from.

Stdlib only (urllib + html.parser) so it runs on a bare Python install.

Usage:
    python scripts/fetch_docs.py                 # all apps
    python scripts/fetch_docs.py --only 1,2,41   # subset
"""
import argparse
import concurrent.futures
import csv
import os
import uuid
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = DATA / "sources"
SOURCES.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# Curated entry points. These are the pages a human would open first for each app.
DOC_OVERRIDES = {
    1: "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_what_is_rest_api.htm",
    2: "https://developers.hubspot.com/docs/api/overview",
    3: "https://developers.pipedrive.com/docs/api/v1",
    4: "https://developers.attio.com/reference",
    5: "https://twenty.com/developers",
    6: "https://developers.podio.com/",
    7: "https://www.zoho.com/crm/developer/docs/api/v8/oauth-overview.html",
    8: "https://developer.close.com/",
    9: "https://developer.copper.com/",
    10: "https://api.docs.dealcloud.com/",
    11: "https://developer.zendesk.com/api-reference/",
    12: "https://developers.intercom.com/docs",
    13: "https://developers.freshdesk.com/api/",
    14: "https://dev.frontapp.com/docs",
    15: "https://docs.usepylon.com/",
    16: "https://developers.liveagent.com/",
    17: "https://docs.plain.com/",
    18: "https://developer.helpscout.com/",
    19: "https://developers.gorgias.com/reference/introduction",
    20: "https://developer.gladly.com/docs",
    21: "https://api.slack.com/authentication",
    22: "https://www.twilio.com/docs/iam/api",
    23: "https://www.zoho.com/cliq/help/restapi/v2/",
    24: "https://open.larksuite.com/document/server-docs/api-call-guide/calling-process/get-access-token",
    25: "https://pumble.com/api",
    26: "https://discord.com/developers/docs/reference",
    27: "https://core.telegram.org/bots/api",
    28: "https://developers.facebook.com/docs/whatsapp/cloud-api.md",
    29: "https://developer.aircall.io/api-references/",
    30: "https://developer.vonage.com/en/api/messages",
    31: "https://developers.google.com/google-ads/api/docs/start",
    32: "https://developers.facebook.com/docs/marketing-apis/",
    33: "https://learn.microsoft.com/en-us/linkedin/marketing/overview",
    34: "https://highlevel.stoplight.io/docs/integrations/",
    35: "https://mailchimp.com/developer/marketing/api/",
    36: "https://developers.klaviyo.com/en/reference/api_overview",
    37: "https://systeme.io/",
    38: "https://developers.pinterest.com/docs/api/v5/introduction/",
    39: "https://developers.facebook.com/docs/threads/overview",
    40: "https://www.twilio.com/docs/sendgrid/api-reference",
    41: "https://shopify.dev/docs/api/admin",
    42: "https://woocommerce.com/document/woocommerce-rest-api/",
    43: "https://developer.bigcommerce.com/docs/rest-management",
    44: "https://developer.salesforce.com/docs/commerce/b2c-commerce/guide/b2c-intro.html",
    45: "https://developer.adobe.com/commerce/webapi/rest/",
    46: "https://developers.squarespace.com/commerce-apis/overview",
    47: "https://api-docs.ecwid.com/reference/overview",
    48: "https://gumroad.com/help/article/280-api",
    83: "https://developers.binance.com/docs/binance-spot-api-docs.md",
    49: "https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api",
    50: "https://fanbasis.com/",
    51: "https://docs.dataforseo.com/v3/",
    52: "https://seranking.com/api/",
    53: "https://ahrefs.com/api/documentation",
    54: "https://docs.mrscraper.com/",
    55: "https://docs.apify.com/api/v2",
    56: "https://docs.firecrawl.dev/introduction",
    57: "https://docs.brightdata.com/api-reference/introduction",
    58: "https://github.com/sherlock-project/sherlock",
    59: "https://waterfall.io/",
    60: "https://docs.clay.com/",
    61: "https://docs.github.com/en/rest",
    62: "https://vercel.com/docs/rest-api",
    63: "https://docs.netlify.com/api/get-started/",
    64: "https://developers.cloudflare.com/api/",
    65: "https://supabase.com/docs/guides/api",
    66: "https://neo4j.com/docs/http-api/current/",
    67: "https://docs.snowflake.com/en/developer-guide/sql-api/index",
    68: "https://www.mongodb.com/docs/atlas/api/atlas-admin-api-ref/",
    69: "https://docs.datadoghq.com/api/latest/",
    70: "https://docs.sentry.io/api/",
    71: "https://developers.notion.com/reference/intro",
    72: "https://airtable.com/developers/web/api/introduction",
    73: "https://developers.linear.app/docs",
    74: "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/",
    75: "https://developers.asana.com/docs",
    76: "https://developer.monday.com/api-reference/docs",
    77: "https://developer.clickup.com/reference",
    78: "https://coda.io/developers/apis/v1",
    79: "https://smartsheet.redoc.ly/",
    80: "https://help.getharvest.com/api-v2/",
    81: "https://docs.stripe.com/api",
    82: "https://plaid.com/docs/api/",
    83: "https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-api-information",
    84: "https://paygent.co.jp/",
    85: "https://ipayx.ai/docs",
    86: "https://developer.intuit.com/app/developer/qbo/docs/get-started",
    87: "https://developer.xero.com/documentation/api/accounting/overview",
    88: "https://developer.brex.com/",
    89: "https://docs.ramp.com/developer-api/v1/overview.md",
    90: "https://pitchbook.com/products/research-api",
    91: "https://notebooklm.google/",
    92: "https://help.otter.ai/",
    93: "https://developers.fathom.video/",
    94: "https://consensus.app/",
    95: "https://docs.reducto.ai/",
    96: "https://docs.devin.ai/",
    97: "https://higgsfield.ai/cli",
    98: "https://github.com/mermaid-js/mermaid-cli",
    99: "https://transcriptapi.com/",
    100: "https://grain.com/",
}

# Fallbacks for apps whose canonical docs page is a JS shell, an error page or behind
# a login. These are plain-HTML pages found by search: an alternate doc host, a
# vendor help-centre article, or a pricing page that states the access rule. They are
# tried *before* the generic guesses, and are labelled `fallback` in the manifest so a
# reader can see the evidence is secondary rather than first-party docs.
FALLBACK_URLS = {
    1: ["https://developer.salesforce.com/docs/platform/api-rest/guide/intro-rest.html",
        "https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/api_rest.pdf"],
    16: ["https://support.liveagent.com/840770-Complete-API-reference",
         "https://support.liveagent.com/741982-API-key"],
    17: ["https://docs.plain.com/docs/graphql/authentication"],
    18: ["https://developer.helpscout.com/mailbox-api/overview/authentication",
         "https://docs.helpscout.com/article/1140-mailbox-api"],
    24: ["https://open.feishu.cn/document/server-docs/api-call-guide/calling-process/get-access-token?lang=en-US"],
    25: ["https://cake-com.github.io/pumble-node-sdk/api-client.html",
         "https://pumble.com/help/integrations/automation-workflow-integrations/api-keys-integration"],
    28: ["https://developers.facebook.com/docs/whatsapp/access-tokens"],
    32: ["https://developers.facebook.com/docs/marketing-api/get-started/authentication",
         "https://developers.facebook.com/docs/marketing-api/access"],
    34: ["https://marketplace.gohighlevel.com/docs/",
         "https://help.gohighlevel.com/support/solutions/articles/48001060529-highlevel-api-documentation"],
    39: ["https://developers.facebook.com/docs/threads/get-started"],
    44: ["https://developer.salesforce.com/docs/commerce/b2c-commerce/guide/scapi-get-started.html"],
    50: ["https://apidocs.fan/"],
    60: ["https://developers.clay.com/quickstart", "https://www.clay.com/pricing"],
    66: ["https://neo4j.com/docs/query-api/current/", "https://neo4j.com/docs/rest-docs/current/",
         "https://neo4j.com/pricing/"],
    83: ["https://developers.binance.com/en/docs/products/spot/rest-api"],
    84: ["https://doc.omnial.io/v1/"],
    85: ["https://www.ipayx.ai/docs/api?lang=en"],
    90: ["https://pitchbook.com/help/PitchBook-api", "https://pitchbook.com/products/research-api"],
    91: ["https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks"],
    93: ["https://developers.fathom.ai/", "https://help.fathom.video/en/articles/8368641-public-api"],
    94: ["https://docs.consensus.app/core-features/api", "https://docs.consensus.app/api-plans-and-access"],
}

SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "template", "iframe"}


class TextExtractor(HTMLParser):
    """Convert HTML to readable text. No third-party dependency, no network."""

    BLOCK = {"p", "div", "br", "li", "tr", "section", "article", "header",
             "footer", "h1", "h2", "h3", "h4", "h5", "h6", "table", "pre",
             "blockquote", "dd", "dt", "td", "th"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag in self.BLOCK and self.skip_depth == 0:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1
        if tag in self.BLOCK and self.skip_depth == 0:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip() + " "
            return
        if self.skip_depth:
            return
        if data.strip():
            self.parts.append(data)

    def text(self):
        raw = "".join(self.parts)
        lines = [re.sub(r"[ \t\u00a0]+", " ", ln).strip() for ln in raw.split("\n")]
        out, blank = [], False
        for ln in lines:
            if ln:
                out.append(ln)
                blank = False
            elif not blank:
                out.append("")
                blank = True
        return "\n".join(out).strip()


def candidates_for(app):
    """Ordered documentation URLs to try for one app."""
    hint = app["hint"].strip()
    name = app["name"].strip()
    clean = re.sub(r"\s*\(.*?\)\s*", "", hint).strip()
    clean = clean.split(" ")[0]
    urls = []
    if clean.startswith("github.com/") or clean.startswith("www."):
        urls.append("https://" + clean)
    elif "/" in clean:
        urls.append("https://" + clean)
    else:
        urls += [
            f"https://docs.{clean}",
            f"https://developers.{clean}",
            f"https://{clean}/docs",
            f"https://developer.{clean}",
            f"https://{clean}/api",
            f"https://{clean}",
        ]
    override = DOC_OVERRIDES.get(int(app["id"]))
    if override:
        urls.insert(0, override)
    fallbacks = FALLBACK_URLS.get(int(app["id"]))
    if fallbacks:
        urls = fallbacks[:1] + ([override] if override else []) + fallbacks[1:] + urls
    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered, name


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(3_000_000)
        charset = resp.headers.get_content_charset() or "utf-8"
        final = resp.geturl()
        status = resp.status
    html = raw.decode(charset, errors="replace")
    if "charset" not in (resp.headers.get("content-type") or "").lower():
        m = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', html[:4000], re.I)
        if m:
            try:
                html = raw.decode(m.group(1), errors="replace")
            except LookupError:
                pass
    return html, status, final


def fetch_curl(url, timeout=25):
    """Second transport: curl with browser headers + HTTP/2 (different TLS fingerprint)."""
    tmp = DATA / f".fetch_tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}.html"
    cmd = ["curl", "-sSL", "--http1.1", "--max-time", str(timeout),
           "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,text/markdown;q=0.9,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "-o", str(tmp), "-w", "%{http_code} %{url_effective}", url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        parts = out.stdout.strip().rsplit(" ", 1)
        status = int(parts[0]) if parts and parts[0].isdigit() else 0
        effective = parts[1] if len(parts) > 1 else url
        if not tmp.exists():
            return None, status, effective, "curl produced no file"
        raw = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        return raw, status, effective, None
    except Exception as e:
        return None, 0, url, f"{type(e).__name__}: {e}"[:200]


def fetch_proxy(url, timeout=45):
    """Third transport: a text-rendering proxy, for hosts that answer 400/403 to any
    automated client (Salesforce, Meta) or serve a JS shell. The saved text is the
    page's rendered text, and the manifest records transport="proxy" plus the proxy
    host, so a reader can see the evidence was rendered rather than fetched raw."""
    tmp = DATA / f".proxy_tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}.txt"
    cmd = ["curl", "-sSL", "--http1.1", "--max-time", str(timeout),
           "-H", "Accept: text/plain", "-o", str(tmp), "-w", "%{http_code}",
           f"https://r.jina.ai/{url}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        status = int(out.stdout.strip()[-3:]) if out.stdout.strip()[-3:].isdigit() else 0
        if not tmp.exists():
            return None, status, url, "proxy produced no file"
        body = tmp.read_text("utf-8", errors="replace")
        tmp.unlink(missing_ok=True)
        return body, status, url, None
    except Exception as e:
        tmp.unlink(missing_ok=True)
        return None, 0, url, f"{type(e).__name__}: {e}"[:200]


ERROR_MARKERS = ("error-background", "page not found", "something went wrong",
                 "404 not found", "this page doesn't exist", "access denied",
                 "enable javascript", "just a moment...")


def good_enough(text, name, url_hint=None):
    """A page is usable only if it is *this app's* API documentation, not a
    marketing homepage, an SPA shell or an error page."""
    if len(text) < 1500:
        return False
    low = text.lower()
    # Only the head: long docs legitimately mention "page not found" further down.
    if any(m in low[:2500] for m in ERROR_MARKERS):
        return False
    # The page must be about this app.
    raw = name.split("(")[0].strip()
    token = re.split(r"[ .]", raw)[0].lower()
    if token not in low:
        return False
    # A CLI/library repo is legitimate evidence even without API keywords: its
    # absence of an HTTP API is itself the finding.
    if url_hint and "github.com/" in url_hint and len(text) > 1500:
        return True

    # ...and must actually document an API surface, with auth or endpoints.
    api_signal = any(k in low for k in ("api", "endpoint", "graphql", "rest"))
    auth_signal = any(k in low for k in ("oauth", "api key", "api-key", "token",
                                         "authentication", "authorization", "bearer"))
    return api_signal and auth_signal


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]


def save_source(app_id, body, meta):
    """Persist the exact text we extracted, plus provenance alongside it."""
    (SOURCES / f"{app_id}.txt").write_text(body, encoding="utf-8")
    (SOURCES / f"{app_id}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def process(app):
    app_id = int(app["id"])
    urls, name = candidates_for(app)
    # Markdown variants: Mintlify/Fern/Amazon docs serve plain markdown for the same path.
    variants = []
    for u in urls:
        variants.append(u)
        if not u.endswith(".md") and not u.endswith(".txt"):
            variants.append(u.rstrip("/") + ".md")
    attempts = []
    for url in variants:
        for transport in ("urllib", "curl", "proxy"):
            try:
                if transport == "urllib":
                    html, status, final = fetch(url)
                elif transport == "curl":
                    html, status, final, err = fetch_curl(url)
                    if err or html is None:
                        attempts.append({"url": url, "transport": transport, "error": err})
                        continue
                else:
                    html, status, final, err = fetch_proxy(url)
                    if err or html is None:
                        attempts.append({"url": url, "transport": transport, "error": err})
                        continue
                if isinstance(html, bytes):
                    html = html.decode("utf-8", errors="replace")
                is_markdown = (url.endswith(".md") or "text/markdown" in html[:200].lower()
                               or transport == "proxy")
                if is_markdown:
                    body = html.strip()
                    title = ""
                else:
                    text = TextExtractor()
                    text.feed(html)
                    body = text.text()
                    title = text.title.strip()
                attempts.append({"url": url, "transport": transport, "status": status,
                                 "final_url": final, "chars": len(body)})
                if good_enough(body, name, final):
                    meta = {
                        "id": app_id, "name": name, "requested_url": url,
                        "final_url": final, "status": status, "chars": len(body),
                        "title": title, "transport": transport,
                        "rendered_via": "r.jina.ai" if transport == "proxy" else "direct",
                        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    }
                    save_source(app_id, body, meta)
                    return {**meta, "ok": True, "attempts": attempts}
            except Exception as e:  # network/HTTP/parse failure is data, not a crash
                attempts.append({"url": url, "transport": transport,
                                 "error": f"{type(e).__name__}: {e}"[:200]})
    return {"id": app_id, "name": name, "ok": False, "attempts": attempts,
            "chars": 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma separated app ids")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    with open(ROOT / "apps.csv", encoding="utf-8-sig") as f:
        apps = list(csv.DictReader(f))
    if args.only:
        keep = {int(x) for x in args.only.split(",") if x.strip()}
        apps = [a for a in apps if int(a["id"]) in keep]

    manifest_path = DATA / "fetch_manifest.json"
    previous = {}
    if manifest_path.exists():
        previous = {str(r["id"]): r for r in json.loads(manifest_path.read_text("utf-8"))}

    t0 = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, rec in enumerate(pool.map(process, apps), 1):
            results.append(rec)
            flag = "OK  " if rec["ok"] else "FAIL"
            print(f"[{i:3d}/{len(apps)}] {flag} {rec['id']:3d} {rec['name'][:28]:28s} "
                  f"{rec.get('chars', 0):7d} chars  {rec.get('final_url') or ''}", flush=True)

    for rec in results:
        previous[str(rec["id"])] = rec
    manifest_path.write_text(
        json.dumps([previous[k] for k in sorted(previous, key=int)], indent=2),
        encoding="utf-8")

    ok = sum(1 for r in results if r["ok"])
    print(f"\nFetched {ok}/{len(results)} pages in {time.time()-t0:.1f}s")
    print(f"Manifest: {manifest_path}")
    if ok < len(results):
        print("Failed ids:", ", ".join(str(r["id"]) for r in results if not r["ok"]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
