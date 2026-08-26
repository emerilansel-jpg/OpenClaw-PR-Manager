"""Streamlit Community Cloud entrypoint — runs OpenClaw PR Manager dashboard."""
import os
import sys
import runpy
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Sync Streamlit Cloud secrets to os.environ
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, (str, int, float, bool)):
                os.environ.setdefault(k, str(v))
except Exception:
    pass

# Execute the main dashboard app cleanly on every rerun
app_path = ROOT_DIR / "dashboard" / "app.py"
runpy.run_path(str(app_path), run_name="__main__")
