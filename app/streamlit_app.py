"""
Backward-compatibility proxy for Streamlit UI.
Forward execution to the canonical presentation module at ui/streamlit_app.py.
"""

import runpy
import os

target_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui", "streamlit_app.py"))
runpy.run_path(target_path, run_name="__main__")