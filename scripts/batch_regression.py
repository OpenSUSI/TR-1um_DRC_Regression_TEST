#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_DRC = REPO_ROOT / "scripts" / "run_drc.py"
CHECK = REPO_ROOT / "scripts" / "check_results.py"


def run_case(gds_path: Path, meta_path: Path, report_path: Path) -> bool:
    """Run DRC for one testcase and check the result."""
    print(f"\n=== Running {meta_path.stem} ===")

    # 1. Run DRC
    subprocess.run(
        ["python3", str(RUN_DRC), str(gds_path), str(report_path)],
        check=True,
    )

    # 2. Check result
    result = subprocess.run(
        ["python3", str(CHECK), str(report_path), str(meta_path)],
        check=False,
    )

    return result.returncode == 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/batch_regression.py <generated_dir>")
        sys.exit(1)

    gen_dir = Path(sys.argv[1]).resolve()

    if not gen_dir.exists():
        print(f"Error: directory not found: {gen_dir}")
        sys.exit(1)

    if not gen_dir.is_dir():
        print(f"Error: not a directory: {gen_dir}")
        sys.exit(1)

    json_files = sorted(gen_dir.glob("*.json"))
    if not json_files:
        print(f"Error: no testcase metadata files (*.json) found in {gen_dir}")
        sys.exit(1)

    # Use directory name for filesystem paths, but use rule_id for human-readable summary.
    report_dir = REPO_ROOT / "reports" / gen_dir.name
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(json_files[0], "r", encoding="utf-8") as f:
        first_meta = json.load(f)

    rule_id = first_meta.get("rule_id", gen_dir.name)

    total = len(json_files)
    passed = 0

    for meta_path in json_files:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        case_name = meta["case_name"]
        gds_path = gen_dir / f"{case_name}.gds"
        report_path = report_dir / f"{case_name}.lyrdb"

        if not gds_path.exists():
            print(f"\n=== Running {case_name} ===")
            print(f"Error: GDS file not found: {gds_path}")
            print(f"FAILED: {case_name}")
            continue

        ok = run_case(gds_path, meta_path, report_path)

        if ok:
            passed += 1
        else:
            print(f"FAILED: {case_name}")

    print("\n=== Summary ===")
    print(f"Rule      : {rule_id}")
    print(f"Total     : {total}")
    print(f"Passed    : {passed}")
    print(f"Failed    : {total - passed}")

    if passed == total:
        print("\nAll cases passed.")
        sys.exit(0)
    else:
        print("\nSome cases failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()