"""
Stage 2: build the evidence digest the extraction model reads.

For each app with a saved source page, pull the sentences that actually carry the
decision-relevant facts (auth, access, API surface, MCP). Everything here is
verbatim from data/sources/<id>.txt -- nothing is generated. The digest is only
a reading aid; the quote binder later verifies against the FULL saved text, so a
digest sentence that is not in the source cannot survive.

Usage: python scripts/make_digest.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = DATA / "sources"

AUTH_KW = ["oauth", "api key", "api-key", "apikey", "bearer", "basic auth",
           "access token", "personal access token", "authentication", "authorization",
           "authenticate", "x-api-key", "credentials"]
ACCESS_KW = ["free", "trial", "sandbox", "developer account", "developer edition",
             "sign up", "pricing", "price", "paid plan", "contact sales",
             "request access", "enterprise", "partner", "approval", "subscription",
             "invite", "beta", "production access", "app review"]
API_KW = ["rest", "graphql", "webhook", "endpoint", "rate limit", "openapi",
          "swagger", "sdk", "mcp", "model context protocol", "base url", "http"]
STOP_KW = ["cookie", "newsletter", "subscribe to", "all rights reserved",
           "privacy policy", "terms of service", "javascript"]


def windows(s, size=280):
    """Split an over-long run into contiguous word-boundary windows (still verbatim)."""
    out, words, cur = [], s.split(), []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) >= size:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def sentences(text):
    text = re.sub(r"\n+", "\n", text)
    chunks = []
    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 45:
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", line):
            s = s.strip()
            if len(s) < 45:
                continue
            if len(s) <= 600:
                chunks.append(s)
            else:
                chunks.extend(windows(s))
    return chunks


def is_noise(s):
    low = s.lower()
    return any(k in low for k in STOP_KW)


def score(s, kws):
    low = s.lower()
    return sum(1 for k in kws if k in low)


def digest_for(app_id, name):
    path = SOURCES / f"{app_id}.txt"
    if not path.exists():
        return None
    text = path.read_text("utf-8", errors="replace")
    meta_path = SOURCES / f"{app_id}.meta.json"
    meta = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}
    sents = [s for s in sentences(text) if not is_noise(s)]
    picked, seen = [], set()

    def take(bucket, limit, cap):
        taken = 0
        for s in sorted(bucket, key=lambda x: -score(x, bucket_kws))[: cap * 4]:
            key = s[:90].lower()
            if key in seen:
                continue
            seen.add(key)
            picked.append(s)
            taken += 1
            if taken >= limit:
                return

    # auth
    bucket_kws = AUTH_KW
    take([s for s in sents if score(s, AUTH_KW) >= 1], 7, 7)
    bucket_kws = ACCESS_KW
    take([s for s in sents if score(s, ACCESS_KW) >= 1], 8, 8)
    bucket_kws = API_KW
    take([s for s in sents if score(s, API_KW) >= 1], 7, 7)
    bucket_kws = ["mcp", "model context protocol"]
    take([s for s in sents if score(s, bucket_kws) >= 1], 3, 3)

    return {
        "id": app_id, "name": name,
        "docs_url": meta.get("final_url") or meta.get("requested_url"),
        "transport": meta.get("transport"),
        "source_chars": len(text),
        "sentences_total": len(sents),
        "digest": picked,
    }


def main():
    apps = json.loads((DATA / "apps.json").read_text("utf-8")) if (DATA / "apps.json").exists() else None
    if apps is None:
        import csv
        with open(ROOT / "apps.csv", encoding="utf-8-sig") as f:
            apps = list(csv.DictReader(f))
    out, missing = [], []
    for a in apps:
        d = digest_for(int(a["id"]), a["name"])
        if d:
            out.append(d)
        else:
            missing.append(int(a["id"]))
    (DATA / "digest.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    md = []
    for d in out:
        md.append(f"\n===== [{d['id']}] {d['name']}  ({d['docs_url']})  "
                  f"src={d['source_chars']}ch sents={d['sentences_total']}\n")
        for s in d["digest"]:
            md.append(f"- {s}\n")
    (DATA / "digest.md").write_text("".join(md), encoding="utf-8")
    print(f"digest for {len(out)} apps, {len(missing)} without source: {missing}")
    print(f"total digest size: {sum(len(' '.join(d['digest'])) for d in out):,} chars")


if __name__ == "__main__":
    main()
