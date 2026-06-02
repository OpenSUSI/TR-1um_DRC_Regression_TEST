from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
TR1UM_ROOT  = REPO_ROOT / "external" / "TR-1um"
DRC_DIR     = TR1UM_ROOT / "libs.tech" / "klayout" / "drc"
DRC_RUNSET  = DRC_DIR / "run.drc"
#KLAYOUT_BIN = "/Applications/klayout.app/Contents/MacOS/klayout"
KLAYOUT_BIN = r"C:\Users\buchi\AppData\Roaming\KLayout\klayout_app.exe"