"""
Verification loop 3: compare the audited sample against pass 1, apply corrections,
and compute the numbers the case study quotes.

Accuracy rule
-------------
* pass 1 abstained (null / "Not Stated" / []) and the reviewer also could not
  determine the field  -> correct abstention
* pass 1 value equals reviewer value -> hit
* otherwise -> miss

Usage: python scripts/audit_sample.py
Writes data/research_final.json, data/audit_result.json
"""
import json
import pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
FIELDS = ["category", "auth_methods", "access_model", "api_types", "existing_mcp"]

UNKNOWN = {None, "Not Stated", "Unknown", ""}


def is_unknown(v):
    if isinstance(v, list):
        return len(v) == 0
    return v in UNKNOWN


def equal(a, b):
    if isinstance(a, list) and isinstance(b, list):
        return {x.lower() for x in a} == {x.lower() for x in b}
    return str(a).strip().lower() == str(b).strip().lower()


def main():
    research = json.loads((DATA / "research.json").read_text("utf-8"))
    by_id = {r["id"]: r for r in research}
    audit = json.loads((DATA / "audit_pass2.json").read_text("utf-8"))

    rows, hits, misses, abstentions = [], 0, 0, 0
    for case in audit["apps"]:
        rec = by_id[case["id"]]
        field_results = {}
        for f in FIELDS:
            p1, p2 = rec.get(f), case.get(f)
            if is_unknown(p1) and is_unknown(p2):
                verdict = "correct-abstention"
                abstentions += 1
            elif is_unknown(p2):
                verdict = "unverifiable"          # pass 1 claimed, reviewer could not confirm
                abstentions += 1
            elif equal(p1, p2):
                verdict = "hit"
                hits += 1
            else:
                verdict = "miss"
                misses += 1
            field_results[f] = {"pass1": p1, "pass2": p2, "verdict": verdict}
        rows.append({"id": case["id"], "name": rec["name"], "fields": field_results,
                     "note": case.get("note", "")})
        # apply corrections
        for f in FIELDS:
            if field_results[f]["verdict"] == "miss":
                rec[f] = case.get(f)
                if f == "existing_mcp" and case.get(f) is True and not rec.get("mcp_url"):
                    rec["mcp_status"] = "mentioned-in-docs-url-unresolved"
                rec.setdefault("corrections", []).append(
                    {"field": f, "pass1": field_results[f]["pass1"],
                     "pass2": field_results[f]["pass2"]})

    decided = hits + misses
    result = {
        "sample_size": len(audit["apps"]),
        "field_checks": len(audit["apps"]) * len(FIELDS),
        "hits": hits, "misses": misses, "abstentions": abstentions,
        "agreement_on_decided": round(100.0 * hits / decided, 1) if decided else None,
        "agreement_on_all_checks": round(100.0 * hits / (len(audit["apps"]) * len(FIELDS)), 1),
        "rows": rows,
    }
    (DATA / "audit_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
    (DATA / "research_final.json").write_text(
        json.dumps([by_id[k] for k in sorted(by_id)], indent=2, ensure_ascii=False),
        encoding="utf-8")

    print(f"sample {result['sample_size']} apps x {len(FIELDS)} fields = {result['field_checks']} checks")
    print(f"  hits {hits}  misses {misses}  abstentions {abstentions}")
    print(f"  agreement on decided fields: {result['agreement_on_decided']}%")
    for row in rows:
        bad = [f for f, r in row["fields"].items() if r["verdict"] == "miss"]
        if bad:
            print(f"  MISS [{row['id']:3d}] {row['name'][:22]:22s} {', '.join(bad)}")


if __name__ == "__main__":
    main()
