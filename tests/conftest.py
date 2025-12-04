# tests/conftest.py
import sys
from pathlib import Path

# Project root = parent of "tests"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Prepend src/ to sys.path so `import init_methods_book` works
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))