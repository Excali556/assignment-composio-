"""
Stage 3 (scripted path): model extraction over saved page text.

Point it at an OpenAI-compatible endpoint and it produces the record shape that
data/bind_evidence.py then verifies. Two providers are supported out of the box:

    GROQ_API_KEY      -> https://api.groq.com/openai/v1   (model: openai/gpt-oss-120b)
    OPENAI_API_KEY    -> https://api.openai.com/v1        (model: gpt-4.1-mini)

Either can be overridden with LLM_BASE_URL / LLM_MODEL (or the provider-specific
variables). Without a key it exits non-zero rather than pretending to work.

    set -a; . ./.env; set +a
    python scripts/extract.py                    # every app with a saved source
    python scripts/extract.py --ids 2,8,41
    python scripts/extract.py --retry-failed     # only ids missing from the out file

Design rule: the model may only propose a value together with a short *hint* -- a phrase
it believes appears on the page. It never writes the final quote; the binder does that,
and drops any claim whose hint cannot be found verbatim.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = DATA / "sources"

DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "openai": "gpt-4.1-mini",
}

SCHEMA = """Return ONE json object, no prose, with exactly these keys:
{
 "id": <int>, "name": <string>, "category": <string>, "one_liner": <string, max 90 chars>,
 "auth_methods": [subset of "OAuth2","API Key","Basic","Token","Bearer Token","JWT","None"],
 "access_model": one of "Free Self-Serve","Free Trial","Paid Plan Required",
                 "Partner / Admin Approval","Enterprise / Contact Sales",
                 "Open Source / Local CLI","Closed Platform","Mixed","Not Stated",
 "access_basis": "explicit" | "inferred" | "not-stated",
 "api_types": [subset of "REST","GraphQL","Webhooks","CLI / Library","SDK"],
 "existing_mcp": true|false|null, "mcp_url": <string|null>,
 "buildable_today": "Yes"|"Partial"|"No"|"Unknown",
 "main_blocker": <short string, "None" if buildable>,
 "evidence": {"auth": <short hint phrase or null>, "access": <hint or null>,
              "api": <hint or null>, "mcp": <hint or null>},
 "confidence": "High"|"Medium"|"Low",
 "notes": <one sentence on anything ambiguous>
}
Rules:
- A hint must be a phrase you actually read in the source text, 4-12 words, copied exactly.
- If the page does not answer a field, use null (auth/api: empty list; access: "Not Stated").
- Never infer an access model from a marketing banner. Use "Not Stated" instead.
"""


def provider_config():
    groq = os.environ.get("GROQ_API_KEY")
    openai = os.environ.get("OPENAI_API_KEY")
    if groq:
        return {"name": "groq", "key": groq,
                "base": os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                "model": os.environ.get("GROQ_MODEL", DEFAULT_MODELS["groq"])}
    if openai:
        return {"name": "openai", "key": openai,
                "base": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.environ.get("OPENAI_MODEL", DEFAULT_MODELS["openai"])}
    sys.exit("No model key. Set GROQ_API_KEY (or OPENAI_API_KEY) in .env, e.g.\n"
             "  set -a; . ./.env; set +a; python scripts/extract.py")


# Free tiers meter tokens per minute, so we send the decision-relevant part of the page
# rather than the whole thing. Selection is sentence-level and keyword-driven; the
# binder later proves every claim against the *full* saved text, so nothing is lost.
SIGNALS = ("auth", "token", "oauth", "api key", "api-key", "apikey", "bearer", "basic ",
           "credential", "scope", "permission", "pricing", "price", "plan", "free", "trial",
           "paid", "enterprise", "contact sales", "subscription", "mcp", "model context protocol",
           "rest", "graphql", "webhook", "endpoint", "sdk", "cli", "rate limit", "quota")


def condense(text, limit=6000):
    sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    picked, used = [], 0
    intro = text[:900].strip()
    if intro:
        picked.append(intro)
        used = len(intro)
    for s in sentences:
        s = s.strip()
        if not (40 <= len(s) <= 400):
            continue
        low = s.lower()
        if not any(k in low for k in SIGNALS):
            continue
        if used + len(s) > limit:
            continue
        picked.append(s)
        used += len(s) + 1
        if used >= limit:
            break
    return "\n".join(picked)


class TokenBucket:
    """Keeps the run inside a provider's tokens-per-minute budget (Groq free tier: 8000)."""

    def __init__(self, tpm):
        self.tpm = tpm
        self.used = []
        self.lock = threading.Lock()

    def take(self, tokens):
        if not self.tpm:
            return
        while True:
            with self.lock:
                now = time.time()
                self.used = [(t, n) for t, n in self.used if now - t < 60]
                if sum(n for _, n in self.used) + tokens <= self.tpm or not self.used:
                    self.used.append((now, tokens))
                    return
                wait = 60 - (now - self.used[0][0]) + 0.5
            time.sleep(max(1.0, wait))


BUCKET = None


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def call_model(cfg, source_text, name, category, app_id, tries=6):
    limit = int(os.environ.get("EXTRACT_CHARS", "6000"))
    last = None
    for attempt in range(tries):
        snippet = condense(source_text, limit)
        prompt = (f"App: {name} (category: {category}).\n"
                  f"Source: the saved developer documentation text below.\n\n"
                  f"{snippet}\n\n{SCHEMA}")
        body = {
            "model": cfg["model"],
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You extract structured facts from documentation. "
                                              "You never guess: unsupported fields are null."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        if attempt == tries - 1:  # last resort: some models reject response_format
            body.pop("response_format", None)
        if BUCKET:
            BUCKET.take(len(prompt) // 4 + 600)
        req = urllib.request.Request(
            f"{cfg['base'].rstrip('/')}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {cfg['key']}",
                     "Content-Type": "application/json",
                     # urllib's default UA is blocked by Cloudflare (HTTP 403, error 1010)
                     "User-Agent": "app-research-pipeline/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read())
            content = payload["choices"][0]["message"]["content"]
            data = parse_json(content)
            data["id"] = app_id
            data["name"] = name
            data["category"] = category
            data["extracted_by"] = f"{cfg['name']}:{cfg['model']}"
            return data, None
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode("utf-8", "replace")
            last = f"HTTP {e.code}: {detail}"
            if e.code == 413:                     # prompt too large for the tier
                limit = max(2000, int(limit * 0.6))
                time.sleep(1)
                continue
            if e.code == 429:                     # honour the provider's own backoff
                m = re.search(r"try again in ([0-9.]+)s", detail)
                time.sleep(float(m.group(1)) + 1 if m else 5 * (attempt + 1))
                continue
            time.sleep(2 * (attempt + 1))
        except Exception as e:  # network, JSON, schema drift
            last = f"{type(e).__name__}: {e}"[:300]
            time.sleep(2 * (attempt + 1))
    return None, last


def load_apps():
    """Name/category for all 100 apps. research_final only holds the researched subset."""
    apps = {}
    csv_path = ROOT / "apps.csv"
    if csv_path.exists():
        import csv as _csv
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in _csv.DictReader(f):
                apps[int(row["id"])] = {"name": row["name"], "category": row["category"]}
    if (DATA / "apps.json").exists():
        for a in json.loads((DATA / "apps.json").read_text("utf-8")):
            apps[int(a["id"])] = a
    if (DATA / "research_final.json").exists():
        for a in json.loads((DATA / "research_final.json").read_text("utf-8")):
            apps[int(a["id"])] = a
    return apps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="", help="comma separated app ids; default all with sources")
    ap.add_argument("--out", default="data/extraction_api.json")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--retry-failed", action="store_true",
                    help="only ids with a source but no record in --out")
    args = ap.parse_args()

    global BUCKET
    cfg = provider_config()
    BUCKET = TokenBucket(int(os.environ.get("LLM_TPM", "7000")))
    apps = load_apps()
    ids = ([int(x) for x in args.ids.split(",") if x.strip()] if args.ids
           else sorted(int(p.stem) for p in SOURCES.glob("*.txt") if p.stem.isdigit()))
    out_path = ROOT / args.out
    existing = {}
    if out_path.exists():
        existing = {r["id"]: r for r in json.loads(out_path.read_text("utf-8"))}
    if args.retry_failed:
        ids = [i for i in ids if i not in existing]

    print(f"provider {cfg['name']} model {cfg['model']} | {len(ids)} apps")

    def work(i):
        src = SOURCES / f"{i}.txt"
        rec = apps.get(i, {"name": f"App {i}", "category": "Unknown"})
        data, err = call_model(cfg, src.read_text("utf-8", errors="replace"),
                               rec["name"], rec["category"], i)
        return i, rec["name"], data, err

    done, failed = len(existing), []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, name, data, err in pool.map(work, ids):
            if data:
                existing[i] = data
                done += 1
                print(f"  ok   {i:3d} {name[:26]:26s} quotes={sum(1 for v in (data.get('evidence') or {}).values() if v)}", flush=True)
            else:
                failed.append({"id": i, "name": name, "error": err})
                print(f"  FAIL {i:3d} {name[:26]:26s} {err}", flush=True)
            out_path.write_text(json.dumps([existing[k] for k in sorted(existing)],
                                           indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nwrote {args.out}: {len(existing)} records ({len(failed)} failed this run)")
    if failed:
        (ROOT / "data/extraction_api_failures.json").write_text(
            json.dumps(failed, indent=2), encoding="utf-8")
        print("failures -> data/extraction_api_failures.json")
    return 0 if len(failed) < len(ids) else 1


if __name__ == "__main__":
    sys.exit(main())
