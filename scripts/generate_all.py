#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import subprocess
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_GENERATOR = REPO_ROOT / "scripts" / "generate_unit_test.py"
GENERATED_SUFFIXES = {".gds", ".json", ".lyrdb"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate all unit-test artifacts from cases.yaml files."
    )
    parser.add_argument(
        "unit_tests_dir",
        help="Root directory of unit tests",
    )
    parser.add_argument(
        "-c",
        "--category",
        action="append",
        help="Run only the specified category (e.g. Cat-1). "
             "Can be specified multiple times.",
    )
    return parser.parse_args()


def normalize_categories(categories: list[str] | None) -> set[str] | None:
    if not categories:
        return None
    return {c.strip() for c in categories if c.strip()}


def load_yaml(path: Path) -> dict:
    """Load and validate a YAML file as a dictionary."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"invalid YAML structure: {path}")

    return data


def load_categories(unit_tests_dir: Path) -> dict[str, str]:
    """
    Load category display names from:
        unit_tests/categories.yaml

    Expected format:
        Cat-1: Prohibited
        Cat-2: WN-AC/AR related
        ...
    """
    categories_path = unit_tests_dir / "categories.yaml"
    if not categories_path.exists():
        return {}

    data = load_yaml(categories_path)

    category_map: dict[str, str] = {}
    for key, value in data.items():
        category = str(key).strip()
        label = str(value).strip()
        if category:
            category_map[category] = label

    return category_map


def category_display_name(category: str, category_map: dict[str, str]) -> str:
    label = category_map.get(category, "").strip()
    if label:
        return f"{category}: {label}"
    return category


def get_category_name(unit_tests_dir: Path, cases_file: Path) -> str | None:
    """
    Extract category name from:
        unit_tests/<CATEGORY>/<RULE>/cases.yaml
    """
    rel = cases_file.relative_to(unit_tests_dir)
    if len(rel.parts) < 3:
        return None
    return rel.parts[0]


def find_case_files(
    unit_tests_dir: Path,
    categories: set[str] | None = None,
) -> list[Path]:
    """
    Recursively find all cases.yaml files under unit_tests_dir.

    If categories is specified, only files under those category directories
    are returned.
    """
    case_files: list[Path] = []

    for cases_file in sorted(unit_tests_dir.rglob("cases.yaml")):
        category = get_category_name(unit_tests_dir, cases_file)
        if category is None:
            print(f"Warning: unexpected path layout: {cases_file}")
            continue

        if categories is not None and category not in categories:
            continue

        case_files.append(cases_file)

    return case_files


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


def run_generator(unit_tests_dir: Path, cases_file: Path) -> bool:
    """
    Run the common unit-test generator for a single cases.yaml.

    Returns:
        True if generation succeeded, otherwise False.
    """
    rule_dir = cases_file.parent
    out_dir = rule_dir / "generated"
    category = get_category_name(unit_tests_dir, cases_file) or "UNKNOWN"

    print(f"\n=== Generating {category}/{rule_dir.name} ===")
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
        print(f"Result          : FAIL ({category}/{rule_dir.name})")
        return False

    print(f"Result          : PASS ({category}/{rule_dir.name})")
    return True


def main() -> None:
    args = parse_args()

    unit_tests_dir = Path(args.unit_tests_dir).resolve()
    categories = normalize_categories(args.category)

    if not unit_tests_dir.exists():
        print(f"Error: directory not found: {unit_tests_dir}")
        sys.exit(1)

    if not unit_tests_dir.is_dir():
        print(f"Error: not a directory: {unit_tests_dir}")
        sys.exit(1)

    if not COMMON_GENERATOR.exists():
        print(f"Error: common generator not found: {COMMON_GENERATOR}")
        sys.exit(1)

    if categories is not None:
        missing = [c for c in sorted(categories) if not (unit_tests_dir / c).is_dir()]
        if missing:
            print("Error: category directory not found:")
            for c in missing:
                print(f"  - {unit_tests_dir / c}")
            sys.exit(1)

    category_map = load_categories(unit_tests_dir)

    case_files = find_case_files(unit_tests_dir, categories)
    if not case_files:
        print(f"Error: no cases.yaml found under {unit_tests_dir}")
        if categories:
            print(f"Category filter : {', '.join(sorted(categories))}")
        sys.exit(1)

    total = len(case_files)
    passed = 0
    failed_rules: list[tuple[str, str]] = []

    category_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "passed": 0}
    )

    for cases_file in case_files:
        category = get_category_name(unit_tests_dir, cases_file) or "UNKNOWN"
        rule_name = cases_file.parent.name

        category_stats[category]["total"] += 1

        ok = run_generator(unit_tests_dir, cases_file)
        if ok:
            passed += 1
            category_stats[category]["passed"] += 1
        else:
            failed_rules.append((category, rule_name))

    print("\n=== Summary ===")
    print(f"Total  : {total}")
    print(f"Passed : {passed}")
    print(f"Failed : {total - passed}")

    print("\n=== Summary by Category ===")
    for category in sorted(category_stats):
        stats = category_stats[category]
        failed = stats["total"] - stats["passed"]
        print(
            f"{category_display_name(category, category_map)}: "
            f"Total={stats['total']}, Passed={stats['passed']}, Failed={failed}"
        )

    if failed_rules:
        print("\n=== Failed Rules ===")
        current_category = None
        for category, rule_name in sorted(failed_rules):
            if category != current_category:
                current_category = category
                print(f"\n[{category_display_name(category, category_map)}]")
            print(f"  - {rule_name}")
        sys.exit(1)

    print("\nAll case generations completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()