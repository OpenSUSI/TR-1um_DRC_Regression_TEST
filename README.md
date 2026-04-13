# TR-1um_DRC_Regression_TEST

This repository provides a regression testing framework for the TR-1um KLayout DRC runset.

# Preparation 
```
git submodule add https://github.com/OpenSUSI/TR-1um.git external/TR-1um
git commit -m "Add TR-1um as submodule"
git push
```

## Directory Structure

The directory structure is organized as follows:

```
TR-1um_DRC_Regression_TEST/
├── external/
│   └── TR-1um/                  # Git submodule: DRC runset source
│       └── libs.tech/klayout/drc/run.drc
│
├── scripts/                    # Core scripts
│   ├── config.py
│   ├── run_drc.py              # Run KLayout DRC
│   ├── check_results.py        # Compare expected vs actual
│   ├── batch_regression.py     # Run all tests (recursive)
│   └── generate_all.py         # Generate all testcases (recursive)
│
├── unit_tests/                 # One directory per rule
│   ├── GC.W1/
│   │   ├── cases.yaml
│   │   ├── generate.py
│   │   ├── README.md
│   │   └── generated/          # Auto-generated (not tracked)
│   │       ├── *.gds
│   │       └── *.json
│   │
│   ├── GC.S1/
│   │   └── ...
│   │
│   └── M1.W1/
│       └── ...
│
├── reports/                    # DRC results (not tracked)
│   ├── GC.W1/
│   ├── GC.S1/
│   └── M1.W1/
│
└── README.md
```

---

## Design Principles

- **Separation of concerns**  
  - DRC rule files are maintained in the TR-1um repository  
  - Regression logic and testcases are maintained in this repository

- **Reproducibility**  
  - The TR-1um repository is included as a Git submodule  
  - Each regression run is tied to a specific commit of the DRC runset

- **Script-based test generation**  
  - Test layouts are generated programmatically (Python), not manually drawn  
  - This ensures consistency and scalability

- **Minimal verification model (initial stage)**  
  - Regression compares the number of violations in `.lyrdb` reports  
  - This can be extended later to include geometry or category checks

---

## Workflow Overview

1. Define testcases in `cases.yaml`
2. Generate GDS test patterns using `generate.py`
3. Run DRC using `run_drc.py`
4. Compare results using `check_results.py`
5. (Optional) Run all cases using `batch_regression.py`

---

## Notes

- The directories `generated/` and `reports/` are excluded from version control.
- KLayout is executed in batch mode using the runset from the TR-1um submodule.
- The working directory for DRC execution is set to ensure proper resolution of `%include` statements in the runset.

## Quick Start

Follow the steps below to run the DRC regression locally.

### 1. Clone the repository (with submodule)
```bash
git clone --recurse-submodules https://github.com/OpenSUSI/TR-1um_DRC_Regression_TEST.git

cd TR-1um_DRC_Regression_TEST

git submodule update --init --recursive
```

### 2. Generate test patterns

```
python3 scripts/generate_all.py unit_tests
```
This will generate:
- GDS test layouts (.gds)
- Metadata files (.json)

### 3. Run DRC regression

```
python3 scripts/batch_regression.py unit_tests
```
This will:
- Execute KLayout DRC using the TR-1um runset
- Generate reports in reports/
- Compare results with expected values
    
### 4. Check results
You should see output like:
```
=== Running pass_w1p9 ===
PASS

=== Running edge_w1p8 ===
PASS

=== Running fail_w1p7 ===
PASS

All cases passed for M1_W1
```
---

## Naming Conventions

To ensure clarity and consistency across the framework, the following naming conventions are used:

- **Rule ID (logical name)**  
  Used for DRC rule identification and report matching  
  Example: `M1.W1`

- **Directory name (filesystem-safe name)**  
  Used for directories and file organization  
  Example: `M1_W1`

- **Case name**  
  Used for individual testcases  
  Example: `pass_w1p9`, `edge_w1p8`, `fail_w1p7`

This separation allows:

- Direct alignment with DRC rule definitions (`M1.W1`)
- Safe and portable filesystem usage (`M1_W1`)

---

## Regression Scope (Current)

The current regression framework validates:

- Violation count consistency
- Rule identification via category matching in `.lyrdb`

Future extensions may include:

- Geometry-based comparison of violations
- Rule coverage metrics
- Parametric sweep testing
- Continuous integration (CI) support