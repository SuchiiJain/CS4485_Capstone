"""Shared pytest configuration.

Adds the repo root to sys.path so `import src.xyz` works regardless of
where pytest is invoked from.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
