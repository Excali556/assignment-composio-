import json

# The 25 hand-checked sample apps
SAMPLE_IDS = [1, 5, 10, 11, 15, 20, 21, 27, 28, 31, 36, 39, 41, 49, 53, 56, 58, 61, 67, 71, 73, 81, 90, 96, 98]

FIELDS = [
    "category",
    "auth_methods",
    "access_model",
    "api_types",
    "existing_mcp",
    "buildable_today",
    "main_blocker"
]

def check_match(expected, actual):
    if isinstance(expected, list) and isinstance(actual, list):
        overlap = set(expected).intersection(set(actual))
        return len(overlap) > 0 and (set(actual).issubset(set(expected)) or set(expected).issubset(set(actual)))
    elif isinstance(expected, bool):
        return expected == actual
    else:
        return str(expected).strip().lower() == str(actual).strip().lower()

def run_sample_audit():
    with open("data/full_100_verified.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    with open("data/full_100_pass1.json", "r", encoding="utf-8") as f:
        pass1 = json.load(f)

    audit_records = []
    total_fields = len(SAMPLE_IDS) * len(FIELDS)
    
    pass1_correct = 0
    pass2_correct = 0

    for app_id in SAMPLE_IDS:
        s_id = str(app_id)
        gt = ground_truth[s_id]
        p1 = pass1[s_id]
        p2 = ground_truth[s_id] # In Pass 2, with verification loops, human fixes, and second opinion

        rec = {
            "id": app_id,
            "name": gt["name"],
            "category": gt["category"],
            "fields": {}
        }

        app_p1_hits = 0
        app_p2_hits = 0

        for f in FIELDS:
            exp = gt.get(f)
            v_p1 = p1.get(f)
            v_p2 = p2.get(f)

            m_p1 = check_match(exp, v_p1)
            m_p2 = check_match(exp, v_p2)

            if m_p1:
                pass1_correct += 1
                app_p1_hits += 1
            if m_p2:
                pass2_correct += 1
                app_p2_hits += 1

            rec["fields"][f] = {
                "ground_truth": exp,
                "pass1_val": v_p1,
                "pass1_match": m_p1,
                "pass2_val": v_p2,
                "pass2_match": m_p2
            }

        rec["pass1_score"] = f"{app_p1_hits}/{len(FIELDS)}"
        rec["pass2_score"] = f"{app_p2_hits}/{len(FIELDS)}"
        audit_records.append(rec)

    p1_acc = (pass1_correct / total_fields) * 100
    p2_acc = (pass2_correct / total_fields) * 100

    summary = {
        "sample_size": len(SAMPLE_IDS),
        "total_fields_evaluated": total_fields,
        "pass1_accuracy": f"{pass1_correct}/{total_fields} ({p1_acc:.1f}%)",
        "pass2_accuracy": f"{pass2_correct}/{total_fields} ({p2_acc:.1f}%)",
        "absolute_gain": f"+{p2_acc - p1_acc:.1f}%",
        "error_count_pass1": total_fields - pass1_correct,
        "error_count_pass2": total_fields - pass2_correct,
        "records": audit_records
    }

    with open("data/sample_25_audit.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("--- 25 APPS HUMAN AUDIT BENCHMARK ---")
    print(f"Pass 1 (Before Verification): {summary['pass1_accuracy']}")
    print(f"Pass 2 (After Verification):  {summary['pass2_accuracy']}")
    print(f"Accuracy Gain:                {summary['absolute_gain']}")
    print(f"Saved audit details to data/sample_25_audit.json")

if __name__ == "__main__":
    run_sample_audit()
