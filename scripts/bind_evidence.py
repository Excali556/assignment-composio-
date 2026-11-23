"""
Stage 3: bind every claim to a verbatim quote and verify it against the saved page.

The extraction step supplies short *hints* (distinctive phrases, not retyped quotes).
This script finds each hint in data/sources/<id>.txt, expands it to the containing
sentence, and stores that as the quote. If a hint cannot be found, the claim it
supports is demoted to null -- a claim without verbatim evidence is never published.

Usage:
    python scripts/bind_evidence.py data/extraction_api.json [more.json ...]
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = DATA / "sources"


TRANS = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
                       "\u2013": "-", "\u2014": "-", "\u00a0": " "})
ENTITIES = {"&amp;": "&", "&quot;": '"', "&#x27;": "'", "&apos;": "'",
            "&lt;": "<", "&gt;": ">", "&nbsp;": " ", "&#39;": "'"}


def norm(s):
    return re.sub(r"\s+", " ", s.translate(TRANS)).strip().lower()


def build_norm(text):
    """Lowercased, whitespace-collapsed, entity-decoded text plus an index map
    back to the original, so a match can be turned into a verbatim original slice."""
    out, pos, i = [], [], 0
    while i < len(text):
        m = re.match(r"&(#[xX]?[0-9a-fA-F]+|[a-zA-Z]+);", text[i:i + 12])
        if m:
            rep = ENTITIES.get(m.group(0).lower(), m.group(0))
            for c in rep.lower():
                out.append(c)
                pos.append(i)
            i += len(m.group(0))
            continue
        ch = text[i].translate(TRANS)
        if ch.isspace():
            if out and out[-1] != " ":
                out.append(" ")
                pos.append(i)
        else:
            out.append(ch.lower())
            pos.append(i)
        i += 1
    return "".join(out), pos


def expand(source_norm, positions, source_orig, hint):
    """Find the hint in normalized text, return the containing sentence from the ORIGINAL."""
    h = norm(hint)
    idx = source_norm.find(h)
    if idx < 0:
        return None, -1
    start = positions[idx]
    end = positions[min(idx + len(h), len(positions) - 1)] + 1
    lo, hi = max(0, start - 500), min(len(source_orig), end + 500)
    window = source_orig[lo:hi]
    rel_s, rel_e = start - lo, end - lo
    left = 0
    for m in re.finditer(r"(?<=[.!?])\s+", window[:rel_s]):
        left = m.end()
    right = len(window)
    m = re.search(r"(?<=[.!?])\s+", window[rel_e:])
    if m:
        right = rel_e + m.start()
    quote = re.sub(r"\s+", " ", window[left:right]).strip()
    if 20 <= len(quote) <= 600:
        return quote, start
    # Sentence is too long (minified docs, tables): fall back to a bounded
    # verbatim window around the match, snapped to word boundaries.
    a = max(0, start - 90)
    b = min(len(source_orig), end + 210)
    frag = source_orig[a:b]
    frag = re.sub(r"^\S*\s", "", frag) if a > 0 else frag
    frag = re.sub(r"\s\S*$", "", frag) if b < len(source_orig) else frag
    frag = re.sub(r"\s+", " ", frag).strip()
    return (frag if 25 <= len(frag) <= 500 else None), start


def verify_quote(source_norm, quote):
    """Deterministic check: the published quote must exist verbatim in the source."""
    return norm(quote) in source_norm


def bind(record):
    sid = record["id"]
    src_path = SOURCES / f"{sid}.txt"
    result = {
        "id": sid, "name": record["name"], "category": record["category"],
        "one_liner": record["one_liner"],
        "auth_methods": record["auth_methods"],
        "access_model": record["access_model"],
        "access_basis": record.get("access_basis"),
        "api_types": record["api_types"],
        "existing_mcp": record["existing_mcp"],
        "mcp_url": record.get("mcp_url"),
        "buildable_today": record["buildable_today"],
        "main_blocker": record["main_blocker"],
        "confidence": record["confidence"],
        "notes": record.get("notes", ""),
        "quotes": {}, "binding": {}, "source": None, "verified": False,
    }
    if not src_path.exists():
        result["binding"] = {k: "no-source" for k in ("auth", "access", "api", "mcp")}
        result["buildable_today"] = "Unknown"
        result["main_blocker"] = "No fetchable documentation"
        return result

    src_orig = src_path.read_text("utf-8", errors="replace")
    src_norm, src_pos = build_norm(src_orig)
    meta_path = SOURCES / f"{sid}.meta.json"
    meta = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}
    result["source"] = {
        "url": meta.get("final_url") or meta.get("requested_url"),
        "fetched_at": meta.get("fetched_at"),
        "transport": meta.get("transport"),
        "chars": len(src_orig),
    }

    evidence = record.get("evidence") or {}
    field_map = {
        "auth": ("auth_methods", ["API Key", "OAuth2", "Basic", "Token", "Bearer Token"]),
        "access": ("access_model", None),
        "api": ("api_types", None),
        "mcp": ("existing_mcp", None),
    }
    for key in ("auth", "access", "api", "mcp"):
        hint = evidence.get(key)
        if not hint:
            result["binding"][key] = "not-stated"
            continue
        quote, idx = expand(src_norm, src_pos, src_orig, hint)
        if not quote:
            result["binding"][key] = "hint-not-found"
            continue
        if not verify_quote(src_norm, quote):
            result["binding"][key] = "quote-mismatch"
            continue
        result["quotes"][key] = quote
        result["binding"][key] = "verified"

    # Demote claims whose evidence did not verify.
    if result["binding"]["auth"] != "verified":
        result["auth_methods"] = []
        result["auth_demoted"] = True
    if result["binding"]["access"] != "verified" and result["access_basis"] == "explicit":
        result["access_model"] = "Not Stated"
        result["access_basis"] = "not-stated"
    if result["binding"]["api"] != "verified":
        result["api_types"] = []
    if result["binding"]["mcp"] != "verified":
        result["existing_mcp"] = False if result["existing_mcp"] else result["existing_mcp"]

    result["verified"] = all(result["binding"][k] == "verified"
                             for k in ("auth", "access", "api"))
    return result


def main(paths):
    records = []
    for p in paths:
        records.extend(json.loads(pathlib.Path(p).read_text("utf-8")))
    out = [bind(r) for r in records]
    out.sort(key=lambda r: r["id"])

    dest = DATA / "research.json"
    merged = {}
    if dest.exists():
        merged = {r["id"]: r for r in json.loads(dest.read_text("utf-8"))}
    for r in out:
        merged[r["id"]] = r
    DATA.joinpath("research.json").write_text(
        json.dumps([merged[k] for k in sorted(merged)], indent=2, ensure_ascii=False),
        encoding="utf-8")

    n = len(out)
    q = sum(1 for r in out if r["quotes"])
    full = sum(1 for r in out if len(r["quotes"]) >= 3)
    print(f"bound {n} records -> data/research.json")
    print(f"  with >=1 verified quote : {q}/{n}")
    print(f"  with auth+access+api    : {full}/{n}")
    for r in out:
        b = r["binding"]
        flags = ",".join(f"{k}:{v}" for k, v in b.items() if v != "verified")
        print(f"  [{r['id']:3d}] {r['name'][:24]:24s} quotes={len(r['quotes'])} "
              f"access={r['access_model'][:20]:20s} {'!' + flags if flags else ''}")


if __name__ == "__main__":
    main(sys.argv[1:])
