"""
Stage 4: aggregate the verified dataset into the patterns the case study reports.

Every figure here is computed from data/research_final.json and data/fetch_manifest.json.
Nothing is typed by hand. Coverage is reported alongside each figure so a reader can
tell how much of the set it rests on.

Usage: python scripts/patterns.py
Writes data/stats.json
"""
import json
import pathlib
from collections import Counter, defaultdict

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

SELF_SERVE = {"Free Self-Serve", "Free Trial", "Open Source / Local CLI"}
GATED = {"Paid Plan Required", "Partner / Admin Approval", "Enterprise / Contact Sales",
         "Closed Platform"}
UNDETERMINED = {"Not Stated", "Unknown"}


def main():
    records = json.loads((DATA / "research_final.json").read_text("utf-8"))
    manifest = {r["id"]: r for r in json.loads((DATA / "fetch_manifest.json").read_text("utf-8"))}
    n = len(records)

    auth = Counter()
    auth_unknown = 0
    for r in records:
        ms = r.get("auth_methods") or []
        if not ms:
            auth_unknown += 1
        for m in ms:
            auth[m] += 1

    access = Counter(r["access_model"] for r in records)
    access_known = sum(v for k, v in access.items() if k not in UNDETERMINED)

    by_cat = defaultdict(lambda: {"total": 0, "self_serve": 0, "gated": 0, "undetermined": 0})
    for r in records:
        c = by_cat[r["category"]]
        c["total"] += 1
        if r["access_model"] in SELF_SERVE:
            c["self_serve"] += 1
        elif r["access_model"] in GATED:
            c["gated"] += 1
        else:
            c["undetermined"] += 1

    mcp = Counter()
    for r in records:
        status = r.get("mcp_status")
        if status == "verified-url":
            mcp["verified"] += 1
        elif status == "mentioned-in-docs-url-unresolved":
            mcp["mentioned"] += 1
        else:
            mcp["none_confirmed"] += 1

    blockers = Counter()
    for r in records:
        blockers[r.get("main_blocker") or "Unknown"] += 1

    fields = ["auth_methods", "access_model", "api_types", "existing_mcp"]
    determined_fields = 0
    for r in records:
        determined_fields += sum(1 for f in fields if r.get(f) not in (None, [], "Not Stated", "Unknown"))
    evidence = sum(len(r.get("quotes") or {}) for r in records)

    fetched = sum(1 for r in manifest.values() if r.get("ok"))
    failed = sorted(i for i, r in manifest.items() if not r.get("ok"))

    stats = {
        "apps_total_in_brief": 100,
        "apps_researched": n,
        "apps_with_fetched_docs": fetched,
        "apps_fetch_failed": len(failed),
        "apps_fetch_failed_ids": failed,
        "fields_determined": determined_fields,
        "fields_possible": n * len(fields),
        "field_coverage_pct": round(100.0 * determined_fields / (n * len(fields)), 1),
        "verified_quotes": evidence,
        "auth": {"distribution": dict(auth.most_common()), "unknown_apps": auth_unknown,
                 "known_apps": n - auth_unknown},
        "access": {"distribution": dict(access.most_common()),
                   "known": access_known,
                   "self_serve": sum(1 for r in records if r["access_model"] in SELF_SERVE),
                   "gated": sum(1 for r in records if r["access_model"] in GATED)},
        "by_category": {k: v for k, v in sorted(by_cat.items())},
        "mcp": dict(mcp),
        "blockers": dict(blockers.most_common()),
    }
    (DATA / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"apps researched {n} | docs fetched {fetched}/100 | fetch failed {len(failed)}")
    print(f"field coverage {stats['field_coverage_pct']}% ({determined_fields}/{n*len(fields)})")
    print(f"verified quotes {evidence}")
    print("auth:", dict(auth.most_common()))
    print("access:", dict(access.most_common()))
    print("mcp:", dict(mcp))
    print("blockers:", dict(blockers.most_common()))
    for k, v in sorted(by_cat.items()):
        print(f"  {k[:34]:34s} self-serve {v['self_serve']} gated {v['gated']} undetermined {v['undetermined']}")


if __name__ == "__main__":
    main()
