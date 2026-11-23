"""
Verification loop: confirm MCP servers exist by fetching them.

A repo or doc page only counts if it (a) returns 2xx and (b) actually mentions the
app. Anything that fails is recorded as unverified and never published as a link.

Usage: python scripts/mcp_check.py
Writes data/mcp_verified.json
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fetch_docs import fetch, fetch_curl, TextExtractor  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

# Candidate MCP locations. These are hypotheses; the check decides what is true.
CANDIDATES = {
    1: ["https://github.com/salesforcecli/mcp"],
    8: ["https://github.com/closeio/close-mcp"],
    14: ["https://github.com/frontapp/front-mcp"],
    21: ["https://github.com/modelcontextprotocol/servers"],
    36: ["https://developers.klaviyo.com/en/docs/klaviyo_mcp_server"],
    41: ["https://shopify.dev/docs/apps/build/storefront-mcp"],
    56: ["https://github.com/firecrawl/firecrawl-mcp-server",
         "https://github.com/mendableai/firecrawl-mcp-server"],
    57: ["https://github.com/brightdata/brightdata-mcp"],
    61: ["https://github.com/github/github-mcp-server"],
    64: ["https://github.com/cloudflare/mcp-server-cloudflare"],
    65: ["https://github.com/supabase-community/mcp-server-supabase"],
    71: ["https://github.com/makenotion/notion-mcp-server"],
    73: ["https://mcp.linear.app/mcp"],
    74: ["https://mcp.atlassian.com/v2/mcp"],
    81: ["https://github.com/stripe/agent-toolkit"],
    96: ["https://docs.devin.ai/integrations/mcp"],
    99: ["https://transcriptapi.com/mcp"],
}


def fetch_text(url):
    for transport in ("urllib", "curl"):
        try:
            if transport == "urllib":
                html, status, final = fetch(url, timeout=20)
                if isinstance(html, bytes):
                    html = html.decode("utf-8", errors="replace")
            else:
                html, status, final, err = fetch_curl(url)
                if err or html is None:
                    continue
                html = html.decode("utf-8", errors="replace")
            t = TextExtractor()
            t.feed(html)
            return status, final, t.text()
        except Exception:
            continue
    return None, url, ""


def main():
    with open(DATA / "research.json", encoding="utf-8") as f:
        records = {r["id"]: r for r in json.load(f)}
    results = {}
    for app_id, urls in CANDIDATES.items():
        rec = records.get(app_id)
        if not rec:
            continue
        token = re.split(r"[ .(]", rec["name"].strip())[0].lower()
        verified = []
        tried = []
        for url in urls:
            status, final, text = fetch_text(url)
            ok = bool(status and 200 <= status < 300 and len(text) > 400
                      and token in text.lower() and "mcp" in text.lower())
            tried.append({"url": url, "status": status, "chars": len(text), "ok": ok})
            if ok:
                verified.append({"url": final, "status": status, "chars": len(text)})
                break
        results[app_id] = {"name": rec["name"], "verified": verified, "attempted": tried}
        mark = "OK " if verified else "---"
        print(f"{mark} [{app_id:3d}] {rec['name'][:24]:24s} "
              f"{verified[0]['url'] if verified else 'no live MCP confirmed'}")

    (DATA / "mcp_verified.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Publish only what was confirmed.
    for app_id, res in results.items():
        rec = records[app_id]
        if res["verified"]:
            rec["existing_mcp"] = True
            rec["mcp_url"] = res["verified"][0]["url"]
            rec["mcp_status"] = "verified-url"
        elif rec.get("existing_mcp") is True:
            rec["mcp_status"] = "mentioned-in-docs-url-unresolved"
            rec["mcp_url"] = None
        else:
            rec["existing_mcp"] = None
            rec["mcp_status"] = "none-confirmed"
    (DATA / "research.json").write_text(
        json.dumps([records[k] for k in sorted(records)], indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"\nconfirmed live MCP endpoints: {sum(1 for r in results.values() if r['verified'])}"
          f" / {len(results)} checked")


if __name__ == "__main__":
    main()
