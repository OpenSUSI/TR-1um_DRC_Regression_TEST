#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import yaml


def extract_rule_id(category: str) -> str:
    """
    Extract a rule_id from a KLayout category string.

    Examples:
        "'AP.WN: AP enclosure < 7.0'" -> "AP.WN"
        "AP.WN: AP enclosure < 7.0"   -> "AP.WN"
        "AP.WN"                       -> "AP.WN"
        ""                            -> ""
    """
    text = category.strip()
    if not text:
        return ""

    # KLayout report may wrap category text with quotes.
    text = text.strip("'\"")

    rule_id = text.split(":", 1)[0].strip()

    # Defensive cleanup in case only the head side contains a quote.
    return rule_id.strip("'\"")


def parse_lyrdb(lyrdb_path: Path) -> tuple[Counter[str], list[str]]:
    """
    Parse a KLayout .lyrdb report file.

    Returns:
        tuple:
            - Counter mapping rule_id -> violation count
            - List of raw category strings for debug output
    """
    tree = ET.parse(lyrdb_path)
    root = tree.getroot()

    counts: Counter[str] = Counter()
    categories: list[str] = []

    for item in root.findall(".//item"):
        category_elem = item.find("category")
        category_text = ""

        if category_elem is not None and category_elem.text:
            category_text = category_elem.text.strip()

        categories.append(category_text)

        rule_id = extract_rule_id(category_text)
        if rule_id:
            counts[rule_id] += 1
        else:
            counts["<unknown>"] += 1

    return counts, categories


def load_cases_yaml(cases_yaml_path: Path) -> dict:
    """
    Load and validate cases.yaml.

    Required top-level keys:
        - rule_id
        - cases
    """
    with cases_yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"invalid YAML structure: {cases_yaml_path}")

    if "rule_id" not in data:
        raise ValueError(f"missing top-level 'rule_id' in {cases_yaml_path}")

    if "cases" not in data or not isinstance(data["cases"], list):
        raise ValueError(f"missing or invalid 'cases' list in {cases_yaml_path}")

    return data


def find_case(cases_data: dict, case_name: str) -> dict:
    """
    Find a testcase entry by case name.
    """
    for case in cases_data["cases"]:
        if not isinstance(case, dict):
            continue
        if str(case.get("name", "")).strip() == case_name:
            return case

    available = [
        str(case.get("name", ""))
        for case in cases_data["cases"]
        if isinstance(case, dict)
    ]
    raise ValueError(
        f"case '{case_name}' not found. available cases: {', '.join(available)}"
    )


def format_counter(counter: Counter[str]) -> list[str]:
    """
    Format a Counter for human-readable output.
    """
    if not counter:
        return ["  (none)"]

    return [f"  {rule_id}: {counter[rule_id]}" for rule_id in sorted(counter)]


def collect_waived_rule_ids(cases_data: dict, case: dict) -> set[str]:
    """
    Collect file-level and case-level waived rule IDs.
    """
    file_waivers = {
        str(rule_id).strip()
        for rule_id in cases_data.get("waive_rule_ids", []) or []
        if str(rule_id).strip()
    }
    case_waivers = {
        str(rule_id).strip()
        for rule_id in case.get("waive_rule_ids", []) or []
        if str(rule_id).strip()
    }
    return file_waivers | case_waivers


def determine_allow_other_rules(cases_data: dict, case: dict) -> bool:
    """
    Determine whether non-target, non-waived rules are allowed.

    Case-level setting overrides file-level setting.
    """
    allow_other_rules = bool(cases_data.get("allow_other_rules", False))
    if "allow_other_rules" in case:
        allow_other_rules = bool(case["allow_other_rules"])
    return allow_other_rules


def main() -> None:
    usage = (
        "Usage:\n"
        "  python3 scripts/check_results.py <report.lyrdb> <cases.yaml> [case_name]\n\n"
        "Notes:\n"
        "  - If [case_name] is omitted, the report file stem is used.\n"
        "  - cases.yaml must contain top-level 'rule_id' and 'cases'."
    )

    if len(sys.argv) not in {3, 4}:
        print(usage)
        sys.exit(1)

    report_path = Path(sys.argv[1]).resolve()
    cases_yaml_path = Path(sys.argv[2]).resolve()
    case_name = sys.argv[3] if len(sys.argv) == 4 else report_path.stem

    if not report_path.exists():
        print(f"Error: report not found: {report_path}")
        sys.exit(1)

    if not cases_yaml_path.exists():
        print(f"Error: cases.yaml not found: {cases_yaml_path}")
        sys.exit(1)

    try:
        cases_data = load_cases_yaml(cases_yaml_path)
        case = find_case(cases_data, case_name)
        counts, raw_categories = parse_lyrdb(report_path)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    target_rule_id = str(cases_data["rule_id"]).strip()
    expected_violations = int(case["expected_violations"])

    waived_rule_ids = collect_waived_rule_ids(cases_data, case)
    allow_other_rules = determine_allow_other_rules(cases_data, case)

    actual_target_violations = counts.get(target_rule_id, 0)

    unexpected_counts: Counter[str] = Counter()
    if not allow_other_rules:
        allowed_rule_ids = {target_rule_id} | waived_rule_ids
        for rule_id, count in counts.items():
            if rule_id not in allowed_rule_ids:
                unexpected_counts[rule_id] = count

    count_ok = actual_target_violations == expected_violations
    unexpected_ok = len(unexpected_counts) == 0
    ok = count_ok and unexpected_ok

    print(f"Rule ID          : {target_rule_id}")
    print(f"Case             : {case_name}")
    print(f"Expected         : {expected_violations}")
    print(f"Actual           : {actual_target_violations}")
    print(f"Allow other rules: {allow_other_rules}")

    if waived_rule_ids:
        print("Waived rules     :")
        for rule_id in sorted(waived_rule_ids):
            print(f"  - {rule_id}")
    else:
        print("Waived rules     : (none)")

    print("All violations   :")
    for line in format_counter(counts):
        print(line)

    if raw_categories:
        print("Categories       :")
        for category in raw_categories:
            print(f"  - {category}")

    if unexpected_counts:
        print("Unexpected rules :")
        for line in format_counter(unexpected_counts):
            print(line)
    else:
        print("Unexpected rules : (none)")

    if not count_ok:
        print("Check            : target rule violation count mismatch")

    if not unexpected_ok:
        print("Check            : unexpected non-waived rule(s) found")

    if ok:
        print("Result           : PASS")
        sys.exit(0)

    print("Result           : FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()