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
│   └── TR-1um/
│
├── scripts/
│   ├── run_drc.py
│   ├── check_results.py
│   ├── batch_regression.py
│   ├── generate_unit_test.py
│   └── generate_all.py
│
├── unit_tests/
│   ├── categories.yaml
│   ├── Cat-1/
│   │   ├── AP_WN/
│   │   │   ├── cases.yaml
│   │   │   └── generated/
│   │   └── ...
│   ├── Cat-2/
│   └── ...
│
├── reports/
│   └── <CATEGORY>/<RULE_DIR>/*.lyrdb
│
└── README.md
```

---

## Category Definition

```yaml
Cat-1: Prohibited
Cat-2: WN-AC/AR related
Cat-3: AP/AN/DP/DN related
Cat-4: GC/CO related
Cat-5: AC/AR/GR related
Cat-6: BEOL related
Cat-7: ESD related
Cat-8: PAD related
Cat-9: Electrical / Optional
```

- Used for display only
- Execution depends on directory structure

---

## Quick Start

```bash
git clone --recurse-submodules https://github.com/OpenSUSI/TR-1um_DRC_Regression_TEST.git
cd TR-1um_DRC_Regression_TEST

python3 scripts/generate_all.py unit_tests
python3 scripts/batch_regression.py unit_tests
```

---

## Category Filtering

```bash
python3 scripts/generate_all.py unit_tests -c Cat-1
python3 scripts/batch_regression.py unit_tests -c Cat-1
```

---

## cases.yaml Example

```yaml
rule_id: AP.WN

layers:
  AP: { number: 3, datatype: 1 }
  WN: { number: 140, datatype: 0 }

cases:
  - name: pass_case
    shapes:
      AP: [8, 8, 22, 22]
      WN: [0, 0, 30, 30]
    expected_violations: 0
```

---

## Summary

- One YAML = one rule
- Category-based structure
- Fully automated regression
