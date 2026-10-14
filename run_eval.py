"""
Backward-compatibility forwarder for evaluation suite.
Delegates to the canonical benchmark test module at tests/benchmark/run_benchmark.py.
"""

import runpy
import os

target_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "tests", "benchmark_eval.py"))
runpy.run_path(target_path, run_name="__main__")