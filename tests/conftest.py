import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RACINE / "src"), str(RACINE)]
