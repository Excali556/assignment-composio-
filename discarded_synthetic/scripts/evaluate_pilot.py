import json
from typing import Dict, Any, List

def evaluate_run(run_path: str, answer_key_path: str) -> Dict[str, Any]:
    with open(run_path, "r", encoding="utf-8") as f:
        run_data = json.load(f)
    with open(answer_key_path, "r", encoding="utf-8") as f:
        answer_key = json.load(f)

    fields_to_check = [
        "category",
        "auth_methods",
        "access_model",
        "api_types",
        "existing_mcp",
        "buildable_today",
        "main_blocker"
    ]

    total_fields = 0
    correct_fields = 0
    app_results = {}
    mistakes_by_cause = {
        "Wrong Source": [],
        "Hallucinated Quote / Fact": [],
        "Bad Judgment / Classification": [],
        "Missed Developer Sandbox / Free Tier": []
    }

    for app_id, truth in answer_key.items():
        pred = run_data.get(app_id, {})
        app_score = 0
        app_total = len(fields_to_check)
        field_eval = {}

        for field in fields_to_check:
            t_val = truth.get(field)
            p_val = pred.get(field)

            # Matching logic
            match = False
            if isinstance(t_val, list) and isinstance(p_val, list):
                # Check list overlap (e.g. auth_methods)
                overlap = set(t_val).intersection(set(p_val))
                match = len(overlap) > 0 and (set(p_val).issubset(set(t_val)) or set(t_val).issubset(set(p_val)))
            elif isinstance(t_val, bool):
                match = (t_val == p_val)
            else:
                match = (str(t_val).strip().lower() == str(p_val).strip().lower())

            if match:
                app_score += 1
                correct_fields += 1
                field_eval[field] = "CORRECT"
            else:
                field_eval[field] = f"MISMATCH (Expected: {t_val}, Got: {p_val})"

            total_fields += 1

        app_results[app_id] = {
            "name": truth["name"],
            "score": f"{app_score}/{app_total}",
            "accuracy": f"{(app_score/app_total)*100:.1f}%",
            "fields": field_eval,
            "run_notes": pred.get("run_notes", "")
        }

    overall_accuracy = (correct_fields / total_fields) * 100 if total_fields else 0.0

    return {
        "run_file": run_path,
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "overall_accuracy": f"{overall_accuracy:.1f}%",
        "app_breakdown": app_results
    }

if __name__ == "__main__":
    import sys
    run_file = sys.argv[1] if len(sys.argv) > 1 else "data/pilot_run_1.json"
    key_file = sys.argv[2] if len(sys.argv) > 2 else "data/pilot_5_answer_key.json"
    
    report = evaluate_run(run_file, key_file)
    print(f"\n==========================================")
    print(f"EVALUATION REPORT: {report['run_file']}")
    print(f"Accuracy: {report['correct_fields']}/{report['total_fields']} ({report['overall_accuracy']})")
    print(f"==========================================\n")
    for app_id, data in report["app_breakdown"].items():
        print(f"[{data['name']}] Score: {data['score']} ({data['accuracy']})")
        for f, res in data["fields"].items():
            if "MISMATCH" in res:
                print(f"   X {f}: {res}")
            else:
                print(f"   ✓ {f}")
        if data["run_notes"]:
            print(f"   Notes: {data['run_notes']}")
        print()
