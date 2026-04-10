# TR-1um DRC Regression Test

KLayout DRC runset and regression test framework for the **TR-1um** (1-micron CMOS) PDK.

## Overview

This project provides:

| Item | Path | Description |
|------|------|-------------|
| DRC runset | `drc/tr1um.drc` | KLayout Ruby DRC script covering all TR-1um layers |
| Test generator | `tests/generate_tests.py` | Generates pass/fail GDS test layouts using the KLayout Python API |
| Regression runner | `tests/regression.sh` | Runs DRC on all test layouts and reports pass/fail |
| CI workflow | `.github/workflows/drc_regression.yml` | GitHub Actions pipeline for automated regression |

---

## Layer Map

| Layer name | GDS layer | Datatype | Description |
|------------|-----------|----------|-------------|
| NWELL      | 1 | 0 | N-type well |
| ACTIVE     | 2 | 0 | Active / OD (oxide definition / diffusion) |
| NPLUS      | 3 | 0 | N+ implant (N-select) |
| PPLUS      | 4 | 0 | P+ implant (P-select) |
| POLY       | 5 | 0 | Poly-silicon gate |
| CONTACT    | 6 | 0 | Contact holes |
| METAL1     | 7 | 0 | Metal 1 |
| VIA1       | 8 | 0 | Via 1 (Metal1–Metal2) |
| METAL2     | 9 | 0 | Metal 2 |
| VIA2       | 10 | 0 | Via 2 (Metal2–Metal3) |
| METAL3     | 11 | 0 | Metal 3 |
| OVERGLASS  | 12 | 0 | Overglass / bond pad opening |

---

## DRC Rules Summary

### NWELL
| Rule ID | Description | Value |
|---------|-------------|-------|
| NWELL.W1 | Minimum NWELL width | 3.0 μm |
| NWELL.S1 | Minimum NWELL–NWELL space | 5.0 μm |
| NWELL.E1 | NWELL enclosure of PMOS active | 1.0 μm |

### ACTIVE (OD)
| Rule ID | Description | Value |
|---------|-------------|-------|
| ACTIVE.W1 | Minimum active width | 2.0 μm |
| ACTIVE.S1 | Minimum active–active space | 2.5 μm |

### NPLUS / PPLUS
| Rule ID | Description | Value |
|---------|-------------|-------|
| NPLUS.W1 | Minimum NPLUS width | 2.0 μm |
| NPLUS.S1 | Minimum NPLUS–NPLUS space | 2.0 μm |
| NPLUS.E1 | NPLUS enclosure of NMOS active | 1.0 μm |
| PPLUS.W1 | Minimum PPLUS width | 2.0 μm |
| PPLUS.S1 | Minimum PPLUS–PPLUS space | 2.0 μm |
| PPLUS.E1 | PPLUS enclosure of PMOS active | 1.0 μm |

### POLY
| Rule ID | Description | Value |
|---------|-------------|-------|
| POLY.W1 | Minimum poly width (minimum gate length) | 1.0 μm |
| POLY.S1 | Minimum poly–poly space | 2.0 μm |
| POLY.E1 | Gate poly extension beyond active | 0.5 μm |
| POLY.SP1 | Routing poly to active space (poly not crossing active) | 0.5 μm |

### CONTACT
| Rule ID | Description | Value |
|---------|-------------|-------|
| CONT.W1 | Minimum contact width | 1.2 μm |
| CONT.S1 | Minimum contact–contact space | 1.2 μm |
| CONT.E1 | Active enclosure of contact | 0.5 μm |
| CONT.E2 | Poly enclosure of contact | 0.5 μm |
| CONT.R1 | Contact must be inside active or poly | — |

### METAL1
| Rule ID | Description | Value |
|---------|-------------|-------|
| MET1.W1 | Minimum Metal1 width | 1.5 μm |
| MET1.S1 | Minimum Metal1–Metal1 space | 2.0 μm |
| MET1.E1 | Metal1 enclosure of contact | 0.5 μm |
| MET1.R1 | Contact must be covered by Metal1 | — |

### VIA1
| Rule ID | Description | Value |
|---------|-------------|-------|
| VIA1.W1 | Minimum Via1 width | 1.5 μm |
| VIA1.S1 | Minimum Via1–Via1 space | 1.5 μm |
| VIA1.E1 | Metal1 enclosure of Via1 | 0.5 μm |
| VIA1.E2 | Metal2 enclosure of Via1 | 0.5 μm |
| VIA1.R1 | Via1 must be inside Metal1 | — |
| VIA1.R2 | Via1 must be inside Metal2 | — |

### METAL2
| Rule ID | Description | Value |
|---------|-------------|-------|
| MET2.W1 | Minimum Metal2 width | 2.0 μm |
| MET2.S1 | Minimum Metal2–Metal2 space | 2.5 μm |

### VIA2
| Rule ID | Description | Value |
|---------|-------------|-------|
| VIA2.W1 | Minimum Via2 width | 1.5 μm |
| VIA2.S1 | Minimum Via2–Via2 space | 1.5 μm |
| VIA2.E1 | Metal2 enclosure of Via2 | 0.5 μm |
| VIA2.E2 | Metal3 enclosure of Via2 | 0.5 μm |
| VIA2.R1 | Via2 must be inside Metal2 | — |
| VIA2.R2 | Via2 must be inside Metal3 | — |

### METAL3
| Rule ID | Description | Value |
|---------|-------------|-------|
| MET3.W1 | Minimum Metal3 width | 2.5 μm |
| MET3.S1 | Minimum Metal3–Metal3 space | 3.0 μm |

### OVERGLASS
| Rule ID | Description | Value |
|---------|-------------|-------|
| OVGLS.W1 | Minimum overglass opening width | 40.0 μm |
| OVGLS.S1 | Minimum overglass–overglass space | 30.0 μm |
| OVGLS.E1 | Metal3 enclosure of pad opening | 10.0 μm |
| OVGLS.R1 | Overglass opening must be inside Metal3 | — |

---

## Quick Start

### Prerequisites

- [KLayout](https://www.klayout.de/) ≥ 0.28 (batch mode, `klayout -b`)
- Python 3.9+ with the `klayout` package (`pip install klayout`)

### 1 – Run DRC on your layout (command line)

```bash
klayout -b \
  -r drc/tr1um.drc \
  -rd input=my_design.gds \
  -rd report=my_design.lyrdb
```

Open `my_design.lyrdb` in KLayout (**Tools → Marker Browser**) to review violations.

### 2 – Run DRC interactively in KLayout

1. Open your GDS in KLayout.
2. Go to **Tools → DRC → New Script**.
3. Load `drc/tr1um.drc`.
4. Click **Run**.

### 3 – Generate test layouts and run regression

```bash
# Generate pass / fail GDS test cases
python tests/generate_tests.py

# Run the full regression suite
bash tests/regression.sh
```

---

## Repository Layout

```
TR-1um_DRC_Regression_TEST/
├── drc/
│   └── tr1um.drc                  # KLayout DRC runset
├── tests/
│   ├── generate_tests.py          # Generates test GDS files
│   ├── regression.sh              # Regression runner
│   ├── gds/
│   │   ├── pass/                  # Layouts that must produce 0 violations
│   │   └── fail/                  # Layouts that must produce ≥ 1 violation
│   └── reports/                   # DRC report output (generated, gitignored)
├── .github/
│   └── workflows/
│       └── drc_regression.yml     # GitHub Actions CI
└── README.md
```

---

## Contributing

1. Fork the repository and create a feature branch.
2. Add or update rules in `drc/tr1um.drc`.
3. Add corresponding test cases in `tests/generate_tests.py`.
4. Run `bash tests/regression.sh` locally to verify all tests pass.
5. Open a pull request — the CI will run the regression automatically.

---

## License

See [LICENSE](LICENSE).
