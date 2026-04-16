#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_GENERATOR = REPO_ROOT / "scripts" / "generate_unit_test.py"
GENERATED_SUFFIXES = {".gds", ".json", ".lyrdb"}


def find_case_files(unit_tests_dir: Path) -> list[Path]:
    """
    Recursively find all cases.yaml files under unit_tests_dir.
    """
    return sorted(unit_tests_dir.rglob("cases.yaml"))


def clean_generated_dir(out_dir: Path) -> None:
    """
    Remove previously generated files from out_dir.

    Only known generated artifacts are removed.
    """
    if not out_dir.exists():
        return

    removed = 0
    for path in out_dir.iterdir():
        if path.is_file() and path.suffix in GENERATED_SUFFIXES:
            path.unlink()
            removed += 1

    if removed > 0:
        print(f"Cleaned         : {removed} file(s) in {out_dir}")


def run_generator(cases_file: Path) -> bool:
    """
    Run the common unit-test generator for a single cases.yaml.

    Returns:
        True if generation succeeded, otherwise False.
    """
    rule_dir = cases_file.parent
    out_dir = rule_dir / "generated"

    print(f"\n=== Generating {rule_dir.name} ===")
    print(f"Cases file      : {cases_file}")
    print(f"Generator       : {COMMON_GENERATOR}")
    print(f"Output dir      : {out_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    clean_generated_dir(out_dir)

    result = subprocess.run(
        ["python3", str(COMMON_GENERATOR), str(cases_file), str(out_dir)],
        check=False,
    )

    if result.returncode != 0:
        print(f"Result          : FAIL ({rule_dir.name})")
        return False

    print(f"Result          : PASS ({rule_dir.name})")
    return True


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/generate_all.py <unit_tests_dir>")
        sys.exit(1)

    unit_tests_dir = Path(sys.argv[1]).resolve()

    if not unit_tests_dir.exists():
        print(f"Error: directory not found: {unit_tests_dir}")
        sys.exit(1)

    if not unit_tests_dir.is_dir():
        print(f"Error: not a directory: {unit_tests_dir}")
        sys.exit(1)

    if not COMMON_GENERATOR.exists():
        print(f"Error: common generator not found: {COMMON_GENERATOR}")
        sys.exit(1)

    case_files = find_case_files(unit_tests_dir)
    if not case_files:
        print(f"Error: no cases.yaml found under {unit_tests_dir}")
        sys.exit(1)

    total = len(case_files)
    passed = 0
    failed_rules: list[str] = []

    for cases_file in case_files:
        ok = run_generator(cases_file)
        if ok:
            passed += 1
        else:
            failed_rules.append(cases_file.parent.name)

    print("\n=== Summary ===")
    print(f"Total  : {total}")
    print(f"Passed : {passed}")
    print(f"Failed : {total - passed}")

    if failed_rules:
        print("\n=== Failed Rules ===")
        for rule_name in failed_rules:
            print(f"  - {rule_name}")
        sys.exit(1)

    print("\nAll case generations completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()