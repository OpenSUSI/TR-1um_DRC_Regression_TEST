# TR-1um_DRC_Regression_TEST

This repository provides a regression testing framework for the TR-1um KLayout DRC runset.

---

# Preparation

```bash
git submodule add https://github.com/OpenSUSI/TR-1um.git external/TR-1um
git commit -m "Add TR-1um as submodule"
git push
```

---

## Directory Structure

```
TR-1um_DRC_Regression_TEST/
├── external/
│   └── TR-1um/                  # Git submodule: DRC runset source
│       └── libs.tech/klayout/drc/run.drc
│
├── scripts/                    # Core scripts
│   ├── config.py
│   ├── run_drc.py              # Run KLayout DRC
│   ├── check_results.py        # Evaluate results (rule_id based + waiver)
│   ├── batch_regression.py     # Run all regression tests
│   ├── generate_unit_test.py   # Common testcase generator
│   └── generate_all.py         # Generate all testcases
│
├── unit_tests/                 # One directory per rule
│   ├── AP_WN/
│   │   ├── cases.yaml          # Test definition (source of truth)
│   │   ├── README.md
│   │   └── generated/          # Auto-generated (not tracked)
│   │       ├── *.gds
│   │       └── *.json
│   │
│   └── ...
│
├── reports/                    # DRC results (not tracked)
│   └── <RULE_DIR>/*.lyrdb
│
└── README.md
```

---

## Design Principles

### Separation of concerns
- DRC rule files → maintained in TR-1um
- Regression framework → maintained in this repository

### Reproducibility
- TR-1um is included as a Git submodule
- Regression tied to a specific DRC runset version

### Script-based generation
- Layouts generated programmatically from YAML
- No manual drawing → reproducible & scalable

### Rule-centric validation
- Validation based on rule_id and violation count
- Waiver mechanism handles side effects

---

## Workflow Overview

1. Define testcases in cases.yaml
2. Generate layouts
3. Run DRC
4. Evaluate results

---

## Quick Start

```bash
git clone --recurse-submodules https://github.com/OpenSUSI/TR-1um_DRC_Regression_TEST.git
cd TR-1um_DRC_Regression_TEST
python3 scripts/generate_all.py unit_tests
python3 scripts/batch_regression.py unit_tests
```

---

## cases.yaml Specification

### Top-level fields

```yaml
rule_id: AP.WN

layers:
  AP: { number: 3, datatype: 1 }
  WN: { number: 140, datatype: 0 }

allow_other_rules: false
waive_rule_ids:
  - GC.R2
  - AR.W1
```

- rule_id: target rule
- layers: layer mapping
- allow_other_rules: strict/loose mode
- waive_rule_ids: ignored rules

---

### cases

```yaml
cases:
  - name: pass_case
    shapes:
      AP: [8, 8, 22, 22]
      WN: [0, 0, 30, 30]
    expected_violations: 0
```

---

### Supported shapes

Rectangle:
```yaml
AP: [x1, y1, x2, y2]
```

Polygon:
```yaml
AP:
  - type: polygon
    points:
      - [0, 0]
      - [10, 0]
      - [10, 10]
```

Octagon:
```yaml
AR:
  - type: octagon
    box: [x1, y1, x2, y2]
    cut: 1.0
```

Donut:
```yaml
GC:
  - type: donut
    outer: [x1, y1, x2, y2]
    inner: [x1, y1, x2, y2]
```

---

## Validation Logic

- target rule count must match expected
- waived rules are ignored
- unexpected rules cause failure (strict mode)

---

## Naming Conventions

- Rule ID: AP.WN
- Directory: AP_WN
- Case: fail_example

---

## Notes

- generated/ and reports/ are not tracked
- JSON is debug metadata
- KLayout runs in batch mode

---

## Summary

- One YAML = one rule
- rule_id-driven validation
- fully automated pipeline
