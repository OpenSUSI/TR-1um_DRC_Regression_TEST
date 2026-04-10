#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

from config import DRC_DIR, DRC_RUNSET, KLAYOUT_BIN

def run_drc(gds_path: str, report_path: str, top_cell: str | None = None):
    gds_abs     = str(Path(gds_path).resolve())
    report_abs  = str(Path(report_path).resolve())

    cmd = [
        KLAYOUT_BIN,
        "-b",
        "-r",
        str(DRC_RUNSET.name),
        "-rd",
        f"input={gds_abs}",
        "-rd",
        f"report={report_abs}",
    ]

    if top_cell:
        cmd += ["-rd", f"top_cell={top_cell}"]

    print("Running:", " ".join(cmd))
    print("CWD:", DRC_DIR)

    subprocess.run(cmd, cwd=DRC_DIR, check=True)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/run_drc.py <input.gds> <report.lyrdb> [top_cell]")
        sys.exit(1)

    input_gds   = sys.argv[1]
    report      = sys.argv[2]
    top         = sys.argv[3] if len(sys.argv) > 3 else None

    run_drc(input_gds, report, top)