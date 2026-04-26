"""
Root conftest for the backend test suite.

Adds the backend/ directory to sys.path so that `import app.*` resolves
regardless of which directory pytest is invoked from (project root or backend/).
"""
import sys
from pathlib import Path

# Ensure backend/ is on the path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
