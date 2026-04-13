#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
from collections import defaultdict


REPO_ROOT   = Path(__file__).resolve().parent.parent
RUN_DRC     = REPO_ROOT / "scripts" / "run_drc.py"
CHECK       = REPO_ROOT / "scripts" / "check_results.py"
DEFAULT_REPORT_ROOT = REPO_ROOT / "reports"


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_testcases(unit_tests_dir: Path) -> list[tuple[str, Path, Path, Path]]:
    """
    Recursively find all regression testcases under unit_tests_dir.

    Expected layout:
        unit_tests/<RULE_ID>/generated/<case_name>.json
        unit_tests/<RULE_ID>/generated/<case_name>.gds

    Returns:
        A list of tuples:
            (rule_id, meta_path, gds_path, rule_dir)
    """
    testcases: list[tuple[str, Path, Path, Path]] = []

    for meta_path in sorted(unit_tests_dir.rglob("generated/*.json")):
        try:
            meta = load_json(meta_path)
        except Exception as e:
            print(f"Warning: failed to read JSON: {meta_path} ({e})")
            continue

        case_name = meta.get("case_name", meta_path.stem)
        rule_id = meta.get("rule_id", meta_path.parent.parent.name)
        gds_path = meta_path.with_suffix(".gds")
        rule_dir = meta_path.parent.parent

        testcases.append((rule_id, meta_path, gds_path, rule_dir))

    return testcases


def run_case(gds_path: Path, meta_path: Path, report_path: Path) -> bool:
    """Run DRC for one testcase and verify the result."""
    case_name = meta_path.stem
    print(f"\n=== Running {case_name} ===")

    try:
        subprocess.run(
            ["python3", str(RUN_DRC), str(gds_path), str(report_path)],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: DRC execution failed for {case_name}")
        print(f"Command: {' '.join(map(str, e.cmd))}")
        print(f"Return code: {e.returncode}")
        return False

    result = subprocess.run(
        ["python3", str(CHECK), str(report_path), str(meta_path)],
        check=False,
    )

    if result.returncode != 0:
        print(f"Check failed: {case_name}")

    return result.returncode == 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/batch_regression.py <unit_tests_dir>")
        sys.exit(1)

    unit_tests_dir = Path(sys.argv[1]).resolve()

    if not unit_tests_dir.exists():
        print(f"Error: directory not found: {unit_tests_dir}")
        sys.exit(1)

    if not unit_tests_dir.is_dir():
        print(f"Error: not a directory: {unit_tests_dir}")
        sys.exit(1)

    testcases = find_testcases(unit_tests_dir)
    if not testcases:
        print(f"Error: no testcase metadata files found under {unit_tests_dir}")
        print("Expected pattern: unit_tests/<RULE_ID>/generated/*.json")
        sys.exit(1)

    DEFAULT_REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    total = 0
    passed = 0
    failed_cases: list[tuple[str, str]] = []

    rule_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})

    for rule_id, meta_path, gds_path, rule_dir in testcases:
        total += 1
        rule_stats[rule_id]["total"] += 1

        case_name = meta_path.stem
        report_dir = DEFAULT_REPORT_ROOT / rule_dir.name
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{case_name}.lyrdb"

        if not gds_path.exists():
            print(f"\n=== Running {case_name} ===")
            print(f"Error: GDS file not found: {gds_path}")
            failed_cases.append((rule_id, case_name))
            continue

        ok = run_case(gds_path, meta_path, report_path)
        if ok:
            passed += 1
            rule_stats[rule_id]["passed"] += 1
        else:
            failed_cases.append((rule_id, case_name))

    print("\n=== Summary (All Rules) ===")
    print(f"Total  : {total}")
    print(f"Passed : {passed}")
    print(f"Failed : {total - passed}")

    print("\n=== Summary by Rule ===")
    for rule_id in sorted(rule_stats.keys()):
        stats = rule_stats[rule_id]
        failed = stats["total"] - stats["passed"]
        print(
            f"{rule_id}: Total={stats['total']}, "
            f"Passed={stats['passed']}, Failed={failed}"
        )

    if failed_cases:
        print("\n=== Failed Cases ===")
        for rule_id, case_name in failed_cases:
            print(f"  - {rule_id} / {case_name}")

    if passed == total:
        print("\nAll cases passed.")
        sys.exit(0)

    print("\nSome cases failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()