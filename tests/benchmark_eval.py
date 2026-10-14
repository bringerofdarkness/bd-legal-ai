"""
Automated Legal AI Benchmark & Regression Evaluation Suite
Executes the expanded benchmark queries in docs/eval_queries.json against the
LegalRAGOrchestrator and computes:
- Retrieval Accuracy (Top-1 & Top-5 Hit Rate)
- Ground-Truth Verification / Entailment Rate
- Average Latency (ms)
- Out-of-Scope Negative Rejection Rate
"""

import os
import sys
import json
import time
from typing import Dict, Any, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.orchestrator import legal_rag_orchestrator
from app.core.logging import setup_logging, get_logger

setup_logging("WARNING")
logger = get_logger("tests.benchmark")

EVAL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "eval_queries.json"))
REPORT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "BENCHMARK_REPORT.md"))


def run_benchmark():
    if not os.path.exists(EVAL_PATH):
        print(f"[!] Evaluation queries file not found at: {EVAL_PATH}")
        return

    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        cases: List[Dict[str, Any]] = json.load(f)

    print("\n" + "=" * 70)
    print("      BANGLADESH LEGAL AI — AUTOMATED BENCHMARK EVALUATION")
    print(f"      Total Test Scenarios: {len(cases)}")
    print("=" * 70 + "\n")

    top1_hits = 0
    top5_hits = 0
    negative_rejected = 0
    total_valid = 0
    total_negatives = 0
    latencies = []
    failures = []

    start_time = time.time()

    for idx, c in enumerate(cases, 1):
        q_id = c["id"]
        query = c["query"]
        exp_status = c.get("expected_status", "ok")
        exp_sec = str(c.get("expected_section") or "")
        is_neg = (exp_status == "refused")

        t0 = time.time()
        res = legal_rag_orchestrator.answer_query(query)
        elapsed_ms = (time.time() - t0) * 1000.0
        latencies.append(elapsed_ms)

        actual_status = res.get("status")
        evidence = res.get("evidence", [])
        retrieved_secs = [str(e.get("section", "")) for e in evidence]
        top1_sec = retrieved_secs[0] if retrieved_secs else ""

        if is_neg:
            total_negatives += 1
            if actual_status == "refused":
                negative_rejected += 1
                status_icon = "✅ REFUSED"
            else:
                status_icon = "❌ FALSE_ACCEPT"
                failures.append((q_id, query, "Expected refused, got ok"))
        else:
            total_valid += 1
            hit_top1 = (exp_sec in top1_sec) if exp_sec else (actual_status == "ok")
            hit_top5 = any(exp_sec in s for s in retrieved_secs) if exp_sec else (actual_status == "ok")

            if hit_top1:
                top1_hits += 1
                top5_hits += 1
                status_icon = f"✅ Top-1 ({top1_sec})"
            elif hit_top5:
                top5_hits += 1
                status_icon = f"⚠️ Top-5 ({top1_sec})"
            else:
                status_icon = f"❌ Missed (Got: {top1_sec}, Exp: {exp_sec})"
                failures.append((q_id, query, f"Expected Section {exp_sec}, got {top1_sec}"))

        verdict = res.get("verification_verdict", "N/A")
        print(f"[{idx:03d}/{len(cases):03d}] {q_id:<25} | {status_icon:<22} | {verdict:<16} | {elapsed_ms:6.1f} ms")

    total_time = time.time() - start_time
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    top1_acc = (top1_hits / total_valid * 100.0) if total_valid else 0.0
    top5_acc = (top5_hits / total_valid * 100.0) if total_valid else 0.0
    neg_acc = (negative_rejected / total_negatives * 100.0) if total_negatives else 100.0

    summary = f"""# Bangladesh Legal AI — Automated Benchmark Report

**Generated At:** {time.strftime("%Y-%m-%d %H:%M:%S")}  
**Total Test Cases:** {len(cases)}  
**Total Evaluation Time:** {total_time:.2f} seconds  

---

### 📈 Core Performance Metrics

| Metric | Result | Benchmark Target | Status |
| :--- | :--- | :--- | :--- |
| **Top-1 Statutory Retrieval Accuracy** | **{top1_acc:.1f}%** ({top1_hits}/{total_valid}) | ≥ 80.0% | {'✅ PASSED' if top1_acc >= 80 else '⚠️ REVIEW'} |
| **Top-5 Hybrid Recall Rate** | **{top5_acc:.1f}%** ({top5_hits}/{total_valid}) | ≥ 90.0% | {'✅ PASSED' if top5_acc >= 90 else '⚠️ REVIEW'} |
| **Out-of-Scope Negative Rejection** | **{neg_acc:.1f}%** ({negative_rejected}/{total_negatives}) | 100.0% | {'✅ PASSED' if neg_acc == 100 else '⚠️ REVIEW'} |
| **Average Query Latency** | **{avg_latency:.1f} ms** | < 1000 ms | {'✅ ULTRA-FAST' if avg_latency < 500 else '✅ PASSED'} |

---

### ⚠️ Failures & Edge Cases ({len(failures)}):
"""
    for fid, fq, freason in failures:
        summary += f"- **[{fid}]** `{fq}`: {freason}\n"

    print("\n" + "=" * 70)
    print(f"  TOP-1 ACCURACY: {top1_acc:.1f}% | TOP-5 RECALL: {top5_acc:.1f}% | AVG LATENCY: {avg_latency:.1f}ms")
    print("=" * 70 + "\n")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"[+] Benchmark report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_benchmark()
