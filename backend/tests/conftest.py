"""Shared pytest fixtures for Cortex backend tests."""

import sys
from pathlib import Path

import pytest

# Ensure the src directory is on the path for imports
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
