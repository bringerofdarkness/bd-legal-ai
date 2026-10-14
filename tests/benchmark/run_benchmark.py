"""
Statutory Benchmark Evaluation Suite
Evaluates full statutory RAG pipeline accuracy, refusal fidelity, and section alignment against gold dataset.
"""

import json
import os
import sys
from collections import Counter

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.pipeline.orchestrator import legal_rag_orchestrator


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

    resp = legal_rag_orchestrator.answer_query(query)

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

    if expected_status == "ok":
        expected_law = case.get("expected_law")
        expected_section = case.get("expected_section")

        result["law_match"] = (actual_law == expected_law)

        if isinstance(expected_section, list):
            result["section_match"] = (actual_section in [str(s).strip() for s in expected_section])
        else:
            result["section_match"] = (actual_section == str(expected_section).strip())

    result["all_passed"] = (
        result["status_match"] and result["law_match"] and result["section_match"]
    )
    return result


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    queries_path = os.path.join(root_dir, "docs", "eval_queries.json")
    results_path = os.path.join(root_dir, "docs", "eval_results.json")

    with open(queries_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    category_counter = Counter()
    category_passed = Counter()

    for case in cases:
        cat = case.get("category", "uncategorized")
        category_counter[cat] += 1

        res = evaluate_case(case)
        results.append(res)

        if res["all_passed"]:
            category_passed[cat] += 1

    total = len(cases)
    passed = sum(1 for r in results if r["all_passed"])
    failed = total - passed

    print("\n" + "=" * 50)
    print("      BANGLADESH LEGAL AI — BENCHMARK RESULTS")
    print("=" * 50)
    print(f"Total Test Cases : {total}")
    print(f"Passed           : {passed}")
    print(f"Failed           : {failed}")
    print(f"Accuracy Score   : {passed / total * 100:.2f}%")
    print("-" * 50)
    print("Breakdown by Category:")
    for cat, count in category_counter.items():
        pass_count = category_passed[cat]
        print(f"  - {cat:<24}: {pass_count}/{count} ({pass_count/count*100:.1f}%)")
    print("=" * 50 + "\n")

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "score_percentage": round(passed / total * 100, 2),
                },
                "category_breakdown": {
                    cat: {
                        "passed": category_passed[cat],
                        "total": count,
                        "percentage": round(category_passed[cat] / count * 100, 2),
                    }
                    for cat, count in category_counter.items()
                },
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    if failed > 0:
        print("Detailed Failures:")
        for r in results:
            if not r["all_passed"]:
                print(
                    f"FAIL: '{r['query']}' | "
                    f"Status match: {r['status_match']} | "
                    f"Law match: {r['law_match']} | "
                    f"Section match: {r['section_match']} | "
                    f"Got section: {r['actual_section']}"
                )
        sys.exit(1)
    else:
        print("ALL TESTS PASSED WITH 100% BENCHMARK INTEGRITY.")


if __name__ == "__main__":
    main()
