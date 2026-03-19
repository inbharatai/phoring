"""Vercel entrypoint for the Phoring Flask backend.

Exposes a module-level ``app`` object so Vercel's Python runtime can
discover and serve the application from repository root.
"""

import os
import sys


BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app


app = create_app()
