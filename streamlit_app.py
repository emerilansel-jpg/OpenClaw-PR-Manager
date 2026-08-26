"""Streamlit Community Cloud entrypoint — runs OpenClaw PR Manager dashboard."""
import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Run main dashboard application
from dashboard.app import *
