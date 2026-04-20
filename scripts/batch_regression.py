#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import subprocess
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_DRC = REPO_ROOT / "scripts" / "run_drc.py"
CHECK_RESULTS = REPO_ROOT / "scripts" / "check_results.py"
DEFAULT_REPORT_ROOT = REPO_ROOT / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run batch DRC regression for generated unit tests."
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


def get_category_name(unit_tests_dir: Path, cases_yaml_path: Path) -> str | None:
    """
    Extract category name from:
        unit_tests/<CATEGORY>/<RULE>/cases.yaml
    """
    rel = cases_yaml_path.relative_to(unit_tests_dir)
    if len(rel.parts) < 3:
        return None
    return rel.parts[0]


def find_testcases(
    unit_tests_dir: Path,
    categories: set[str] | None = None,
) -> list[tuple[str, str, str, Path, Path, Path]]:
    """
    Recursively find all regression testcases under unit_tests_dir.

    Expected layout:
        unit_tests/<CATEGORY>/<RULE_DIR>/cases.yaml
        unit_tests/<CATEGORY>/<RULE_DIR>/generated/<case_name>.gds

    Expected cases.yaml format:
        rule_id: <RULE_ID>
        cases:
          - name: <case_name>
            ...

    Returns:
        List of tuples:
            (category, rule_id, case_name, cases_yaml_path, gds_path, rule_dir)
    """
    testcases: list[tuple[str, str, str, Path, Path, Path]] = []

    for cases_yaml_path in sorted(unit_tests_dir.rglob("cases.yaml")):
        category = get_category_name(unit_tests_dir, cases_yaml_path)
        if category is None:
            print(f"Warning: unexpected path layout: {cases_yaml_path}")
            continue

        if categories is not None and category not in categories:
            continue

        rule_dir = cases_yaml_path.parent

        try:
            data = load_yaml(cases_yaml_path)
        except Exception as exc:
            print(f"Warning: failed to read YAML: {cases_yaml_path} ({exc})")
            continue

        rule_id = str(data.get("rule_id", rule_dir.name)).strip()
        cases = data.get("cases", [])

        if not isinstance(cases, list):
            print(f"Warning: 'cases' is not a list: {cases_yaml_path}")
            continue

        for case in cases:
            if not isinstance(case, dict):
                print(f"Warning: invalid case entry in {cases_yaml_path}: {case!r}")
                continue

            case_name = str(case.get("name", "")).strip()
            if not case_name:
                print(f"Warning: case without name in {cases_yaml_path}")
                continue

            gds_path = rule_dir / "generated" / f"{case_name}.gds"
            testcases.append(
                (category, rule_id, case_name, cases_yaml_path, gds_path, rule_dir)
            )

    return testcases


def run_case(
    category: str,
    case_name: str,
    gds_path: Path,
    cases_yaml_path: Path,
    report_path: Path,
) -> bool:
    """
    Run DRC for one testcase and verify the result.

    Returns:
        True if both DRC run and result check succeed, otherwise False.
    """
    print(f"\n=== Running {category} / {case_name} ===")

    try:
        subprocess.run(
            ["python3", str(RUN_DRC), str(gds_path), str(report_path)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error: DRC execution failed for {case_name}")
        print(f"Command     : {' '.join(map(str, exc.cmd))}")
        print(f"Return code : {exc.returncode}")
        return False

    result = subprocess.run(
        [
            "python3",
            str(CHECK_RESULTS),
            str(report_path),
            str(cases_yaml_path),
            str(case_name),
        ],
        check=False,
    )

    if result.returncode != 0:
        print(f"Check failed: {category} / {case_name}")

    return result.returncode == 0


def category_display_name(category: str, category_map: dict[str, str]) -> str:
    label = category_map.get(category, "").strip()
    if label:
        return f"{category}: {label}"
    return category


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

    if categories is not None:
        missing = [c for c in sorted(categories) if not (unit_tests_dir / c).is_dir()]
        if missing:
            print("Error: category directory not found:")
            for c in missing:
                print(f"  - {unit_tests_dir / c}")
            sys.exit(1)

    category_map = load_categories(unit_tests_dir)

    testcases = find_testcases(unit_tests_dir, categories)
    if not testcases:
        print(f"Error: no testcases found under {unit_tests_dir}")
        if categories:
            print(f"Category filter : {', '.join(sorted(categories))}")
        print("Expected layout:")
        print("  unit_tests/<CATEGORY>/<RULE_DIR>/cases.yaml")
        print("  unit_tests/<CATEGORY>/<RULE_DIR>/generated/<case_name>.gds")
        sys.exit(1)

    DEFAULT_REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    total = 0
    passed = 0
    failed_cases: list[tuple[str, str, str]] = []

    category_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "passed": 0}
    )
    rule_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "passed": 0}
    )

    for category, rule_id, case_name, cases_yaml_path, gds_path, rule_dir in testcases:
        total += 1

        category_stats[category]["total"] += 1
        rule_key = f"{category}/{rule_id}"
        rule_stats[rule_key]["total"] += 1

        report_dir = DEFAULT_REPORT_ROOT / category / rule_dir.name
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{case_name}.lyrdb"

        if not gds_path.exists():
            print(f"\n=== Running {category} / {case_name} ===")
            print(f"Error: GDS file not found: {gds_path}")
            failed_cases.append((category, rule_id, case_name))
            continue

        ok = run_case(category, case_name, gds_path, cases_yaml_path, report_path)
        if ok:
            passed += 1
            category_stats[category]["passed"] += 1
            rule_stats[rule_key]["passed"] += 1
        else:
            failed_cases.append((category, rule_id, case_name))

    print("\n=== Summary (All Rules) ===")
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

    print("\n=== Summary by Rule ===")
    for category in sorted(category_stats):
        print(f"\n[{category_display_name(category, category_map)}]")
        for rule_key in sorted(rule_stats):
            rule_category, rule_id = rule_key.split("/", 1)
            if rule_category != category:
                continue
            stats = rule_stats[rule_key]
            failed = stats["total"] - stats["passed"]
            print(
                f"  {rule_id}: Total={stats['total']}, "
                f"Passed={stats['passed']}, Failed={failed}"
            )

    if failed_cases:
        print("\n=== Failed Cases ===")
        current_category = None
        for category, rule_id, case_name in sorted(failed_cases):
            if category != current_category:
                current_category = category
                print(f"\n[{category_display_name(category, category_map)}]")
            print(f"  - {rule_id} / {case_name}")

    if passed == total:
        print("\nAll cases passed.")
        sys.exit(0)

    print("\nSome cases failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()