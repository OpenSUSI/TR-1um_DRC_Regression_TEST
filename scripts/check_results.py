#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET


def parse_lyrdb(lyrdb_path: Path):
    tree    = ET.parse(lyrdb_path)
    root    = tree.getroot()

    items   = root.findall(".//item")
    categories = []

    for item in items:
        cat = item.find("category")
        categories.append(cat.text.strip() if cat is not None and cat.text else "")

    return len(items), categories


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/check_results.py <report.lyrdb> <meta.json>")
        sys.exit(1)

    report_path = Path(sys.argv[1]).resolve()
    meta_path   = Path(sys.argv[2]).resolve()

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    rule_id     = str(meta["rule_id"])
    case_name   = str(meta["case_name"])
    expected    = int(meta["expected_violations"])

    actual, categories = parse_lyrdb(report_path)

    print(f"Rule       : {rule_id}")
    print(f"Case       : {case_name}")
    print(f"Expected   : {expected}")
    print(f"Actual     : {actual}")

    if categories:
        print("Categories :")
        for c in categories:
            print(f"  - {c}")

    count_ok = (actual == expected)

    category_ok = True
    if expected > 0:
        category_ok = any(rule_id in c for c in categories)

    ok = count_ok and category_ok

    if not count_ok:
        print("Check      : violation count mismatch")

    if expected > 0 and not category_ok:
        print("Check      : rule_id not found in categories")

    if ok:
        print("Result     : PASS")
        sys.exit(0)
    else:
        print("Result     : FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()