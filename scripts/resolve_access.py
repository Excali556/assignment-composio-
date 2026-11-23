"""
Verification loop 2: resolve commercial access from pricing pages.

Most API references never say whether you can actually get credentials for free.
This stage fetches each app's pricing page, stores it as a second source, and pulls
the sentences that speak to signup, free tiers, trials, plan requirements or
sales gates. A human then reads those sentences and sets the access verdict.

Usage: python scripts/resolve_access.py [--report]
"""
import json
import pathlib
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fetch_docs import fetch, fetch_curl, TextExtractor  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
SOURCES = DATA / "sources"

PATHS = ["/pricing", "/pricing/", "/plans", "/plans/", "/pricing.html"]
ACCESS_RE = re.compile(
    r"(free (tier|plan|account|trial|sandbox)|start for free|no credit card|"
    r"contact sales|talk to sales|request (a )?(demo|access)|enterprise|"
    r"per (user|seat|month)|paid plan|upgrade|trail|trial)", re.I)


def candidates(record):
    url = (record.get("source") or {}).get("url") or ""
    host = urlparse(url).netloc
    if not host:
        return []
    root = host[4:] if host.startswith("www.") else host
    return [f"https://{host}{p}" for p in PATHS] + [f"https://{root}{p}" for p in PATHS]


def get_text(url):
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
            body = t.text()
            if len(body) > 800:
                return status, final, body
        except Exception:
            continue
    return None, url, ""


def sentences(text):
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 40:
            continue
        for s in re.split(r"(?<=[.!?])\s+", line):
            s = s.strip()
            if 40 <= len(s) <= 300:
                out.append(s)
    return out


def main():
    records = json.loads((DATA / "research.json").read_text("utf-8"))
    unresolved = [r for r in records if r["access_model"] == "Not Stated"]
    report = []
    resolved = 0
    for rec in unresolved:
        got = None
        for url in candidates(rec):
            status, final, body = get_text(url)
            if body:
                got = (status, final, body)
                break
        if not got:
            report.append({"id": rec["id"], "name": rec["name"], "found": False})
            print(f"--- [{rec['id']:3d}] {rec['name'][:24]:24s} no pricing page")
            continue
        status, final, body = got
        (SOURCES / f"{rec['id']}_pricing.txt").write_text(body, encoding="utf-8")
        hits = [s for s in sentences(body) if ACCESS_RE.search(s)][:3]
        report.append({"id": rec["id"], "name": rec["name"], "found": True,
                       "url": final, "chars": len(body), "sentences": hits})
        resolved += 1
        print(f"OK  [{rec['id']:3d}] {rec['name'][:24]:24s} {len(body):6d}ch {final}")
        for h in hits:
            print(f"       - {h[:150]}")

    (DATA / "access_candidates.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nfetched pricing pages for {resolved}/{len(unresolved)} unresolved apps")


if __name__ == "__main__":
    main()
