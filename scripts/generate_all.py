#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent


def find_generators(unit_tests_dir: Path) -> list[Path]:
    """Recursively find all generate.py files under unit_tests_dir."""
    return sorted(unit_tests_dir.rglob("generate.py"))


def clean_generated_dir(out_dir: Path) -> None:
    """Remove existing generated files (gds/json/etc) in the directory."""
    if not out_dir.exists():
        return

    removed = 0
    for p in out_dir.glob("*"):
        if p.is_file() and p.suffix in {".gds", ".json", ".lyrdb"}:
            p.unlink()
            removed += 1

    if removed > 0:
        print(f"  Cleaned {removed} files in {out_dir}")


def run_generator(generator_path: Path) -> bool:
    """
    Run one generate.py after cleaning its generated directory.
    """
    rule_dir = generator_path.parent
    out_dir = rule_dir / "generated"

    print(f"\n=== Generating: {rule_dir.name} ===")
    print(f"Generator : {generator_path}")
    print(f"Output    : {out_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    # 既存ファイル削除
    clean_generated_dir(out_dir)

    result = subprocess.run(
        ["python3", str(generator_path), str(out_dir)],
        check=False,
    )

    if result.returncode != 0:
        print(f"FAILED: {rule_dir.name}")
        return False

    print(f"OK: {rule_dir.name}")
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

    generators = find_generators(unit_tests_dir)
    if not generators:
        print(f"Error: no generate.py found under {unit_tests_dir}")
        sys.exit(1)

    total = len(generators)
    passed = 0
    failed_rules: list[str] = []

    for generator_path in generators:
        ok = run_generator(generator_path)
        if ok:
            passed += 1
        else:
            failed_rules.append(generator_path.parent.name)

    print("\n=== Summary ===")
    print(f"Total  : {total}")
    print(f"Passed : {passed}")
    print(f"Failed : {total - passed}")

    if failed_rules:
        print("\nFailed rules:")
        for rule_name in failed_rules:
            print(f"  - {rule_name}")
        sys.exit(1)

    print("\nAll generators completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()