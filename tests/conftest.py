import sys
from pathlib import Path

# Also supports running pytest without installing the editable package first.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
