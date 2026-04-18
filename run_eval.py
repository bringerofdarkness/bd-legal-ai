import json
from collections import Counter
from unittest import result
from app.rag_backend import answer_query


def detect_law_and_section(resp):
    evidence = resp.get("evidence", [])
    if not evidence:
        return None, None

    top = evidence[0]
    act = (top.get("act") or "").lower()
    section = str(top.get("section") or "").strip()

    law = None
    if "penal code" in act:
        law = "penal_code"
    elif "contract act" in act:
        law = "contract_act"

    return law, section

def get_top_evidence(resp):
    evidence = resp.get("evidence", [])
    if not evidence:
        return None

    top = evidence[0]
    return {
        "act": top.get("act"),
        "section": top.get("section"),
        "text": top.get("text"),
    }


def evaluate_case(case):
    query = case["query"]
    expected_status = case["expected_status"]

    resp = answer_query(query)

    actual_status = resp.get("status")
    actual_law, actual_section = detect_law_and_section(resp)
    top_evidence = get_top_evidence(resp)

    result = {
        "query": query,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "status_match": actual_status == expected_status,
        "expected_law": case.get("expected_law"),
        "actual_law": actual_law,
        "law_match": True,
        "expected_section": case.get("expected_section"),
        "actual_section": actual_section,
        "section_match": True,
        "top_evidence": top_evidence,
    }

    if "expected_law" in case:
        result["law_match"] = actual_law == case["expected_law"]

    if "expected_section" in case:
        result["section_match"] = actual_section == str(case["expected_section"])

    result["pass"] = (
        result["status_match"]
        and result["law_match"]
        and result["section_match"]
    )

    error_type = None

    if not result["status_match"]:
         error_type = "status_error"
    elif not result["law_match"]:
        error_type = "law_error"
    elif not result["section_match"]:
        error_type = "section_error"

    result["error_type"] = error_type

    return result


def main():
    with open("docs/eval_queries.json", "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = [evaluate_case(case) for case in cases]

    category_totals = Counter(case.get("category", "unknown") for case in cases)
    category_passed = Counter(
        case.get("category", "unknown")
        for case, result in zip(cases, results)
        if result["pass"]
    )

    law_totals = Counter(case.get("law", "unknown") for case in cases)
    law_passed = Counter(
        case.get("law", "unknown")
        for case, result in zip(cases, results)
        if result["pass"]
    )
    total = len(results)
    passed = sum(r["pass"] for r in results)
    failed = total - passed

    print("\n=== Evaluation Summary ===")
    print(f"Total:  {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Score:  {passed}/{total}")

    print("\n=== Category Breakdown ===")
    for category in category_totals:
        print(f"{category}: {category_passed[category]}/{category_totals[category]}")

    print("\n=== Law Breakdown ===")
    for law in law_totals:
        print(f"{law}: {law_passed[law]}/{law_totals[law]}")

    if passed < total:
        exit(1)

    error_counts = Counter(r["error_type"] for r in results if not r["pass"])

    print("\n=== Error Breakdown ===")
    if error_counts:
        for k, v in error_counts.items():
            print(f"{k}: {v}")
    else:
        print("No errors.")

    print("\n=== Failed Cases ===")
    any_failed = False
    for r in results:
        if not r["pass"]:
            any_failed = True
            print("\n----------------------------")
            print("Query:", r["query"])
            print("Expected status:", r["expected_status"])
            print("Actual status:  ", r["actual_status"])
            print("Expected law:   ", r["expected_law"])
            print("Actual law:     ", r["actual_law"])
            print("Expected sec:   ", r["expected_section"])
            print("Actual sec:     ", r["actual_section"])
            print("Top evidence:   ", r["top_evidence"])

    if not any_failed:
        print("No failed cases.")

        category_summary = {
        k: f"{category_passed[k]}/{category_totals[k]}"
        for k in category_totals
    }

    law_summary = {
        k: f"{law_passed[k]}/{law_totals[k]}"
        for k in law_totals
    }

    final_output = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "category_breakdown": category_summary,
        "law_breakdown": law_summary,
        "results": results
    }

    with open("docs/eval_results.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print("\nSaved detailed results to eval_results.json")


if __name__ == "__main__":
    main()