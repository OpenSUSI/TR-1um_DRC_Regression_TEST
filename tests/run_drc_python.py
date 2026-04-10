#!/usr/bin/env python3
"""
run_drc_python.py – Python-based DRC runner for TR-1um PDK
===========================================================
Uses the KLayout Python API (klayout.db) to execute the same DRC checks
defined in drc/tr1um.drc.  This script is the CI alternative for
environments where the ``klayout`` CLI is not installed.

Exit codes
----------
0  all tests passed
1  one or more tests failed

Usage
-----
    python tests/run_drc_python.py [--gds-dir tests/gds] [--verbose]
"""

import argparse
import os
import sys

try:
    import klayout.db as db
except ImportError:
    sys.exit(
        "ERROR: klayout Python package not found.\n"
        "Install with:  pip install klayout"
    )

# ---------------------------------------------------------------------------
# Layer numbers
# ---------------------------------------------------------------------------
L_NWELL    = (1,  0)
L_ACTIVE   = (2,  0)
L_NPLUS    = (3,  0)
L_PPLUS    = (4,  0)
L_POLY     = (5,  0)
L_CONTACT  = (6,  0)
L_METAL1   = (7,  0)
L_VIA1     = (8,  0)
L_METAL2   = (9,  0)
L_VIA2     = (10, 0)
L_METAL3   = (11, 0)
L_OVERGLASS = (12, 0)


# ---------------------------------------------------------------------------
# DRC helpers
# ---------------------------------------------------------------------------

class DRCResult:
    def __init__(self):
        self.violations: list[tuple[str, str]] = []

    def add(self, rule_id: str, message: str) -> None:
        self.violations.append((rule_id, message))

    def count(self) -> int:
        return len(self.violations)


def get_region(layout: db.Layout, cell: db.Cell, layer_info: tuple) -> db.Region:
    """Return a Region for the given (layer, datatype) pair."""
    idx = layout.find_layer(*layer_info)
    if idx is None:
        return db.Region()
    return db.Region(cell.begin_shapes_rec(idx))


def check_width(region: db.Region, min_um: float, dbu: float,
                rule_id: str, description: str, result: DRCResult) -> None:
    min_dbu = int(round(min_um / dbu))
    violations = region.width_check(min_dbu)
    if not violations.is_empty():
        result.add(rule_id, f"{description} (min={min_um} μm)")


def check_space(region: db.Region, min_um: float, dbu: float,
                rule_id: str, description: str, result: DRCResult) -> None:
    min_dbu = int(round(min_um / dbu))
    violations = region.space_check(min_dbu)
    if not violations.is_empty():
        result.add(rule_id, f"{description} (min={min_um} μm)")


def check_enclosure(outer: db.Region, inner: db.Region, min_um: float, dbu: float,
                    rule_id: str, description: str, result: DRCResult) -> None:
    """Check that *outer* encloses *inner* by at least min_um."""
    check_region = inner & outer
    if check_region.is_empty():
        return
    min_dbu = int(round(min_um / dbu))
    violations = outer.enclosing_check(check_region, min_dbu)
    if not violations.is_empty():
        result.add(rule_id, f"{description} (min={min_um} μm)")


def check_not_outside(inner: db.Region, outer: db.Region,
                      rule_id: str, description: str, result: DRCResult) -> None:
    """Check that *inner* is fully contained in *outer*."""
    outside = inner - outer
    if not outside.is_empty():
        result.add(rule_id, description)


def _check_poly_extension(non_gate: db.Region, min_um: float, dbu: float,
                          result: DRCResult) -> None:
    """POLY.E1 – gate poly must extend beyond active by at least min_um.

    The non-gate poly (poly minus active) at each gate end is a rectangular
    strip whose short dimension equals the extension length.  A width check
    on non_gate with the required minimum catches under-extended end caps while
    leaving pure routing poly (which is always >= POLY.W1 >= 1.0 um wide)
    unaffected.
    """
    if non_gate.is_empty():
        return
    min_dbu = int(round(min_um / dbu))
    violations = non_gate.width_check(min_dbu)
    if not violations.is_empty():
        result.add("POLY.E1", f"Gate poly extension beyond active < {min_um} μm")


def run_drc(gds_path: str) -> DRCResult:
    """Run all TR-1um DRC rules on *gds_path* and return violations."""
    layout = db.Layout()
    layout.read(gds_path)
    dbu = layout.dbu
    top = layout.top_cell()
    result = DRCResult()

    # ---- Layer inputs -------------------------------------------------------
    nwell     = get_region(layout, top, L_NWELL)
    active    = get_region(layout, top, L_ACTIVE)
    nplus     = get_region(layout, top, L_NPLUS)
    pplus     = get_region(layout, top, L_PPLUS)
    poly      = get_region(layout, top, L_POLY)
    contact   = get_region(layout, top, L_CONTACT)
    metal1    = get_region(layout, top, L_METAL1)
    via1      = get_region(layout, top, L_VIA1)
    metal2    = get_region(layout, top, L_METAL2)
    via2      = get_region(layout, top, L_VIA2)
    metal3    = get_region(layout, top, L_METAL3)
    overglass = get_region(layout, top, L_OVERGLASS)

    # ---- Derived layers -----------------------------------------------------
    gate          = poly & active
    non_gate      = poly - active
    active_nmos   = active & nplus
    active_pmos   = active & pplus
    active_nwell  = active & nwell

    # ---- NWELL rules --------------------------------------------------------
    check_width(nwell,  3.0, dbu, "NWELL.W1", "NWELL minimum width", result)
    check_space(nwell,  5.0, dbu, "NWELL.S1", "NWELL minimum space", result)
    check_enclosure(nwell, active_nwell, 1.0, dbu,
                    "NWELL.E1", "NWELL enclosure of PMOS active", result)

    # ---- ACTIVE rules -------------------------------------------------------
    check_width(active, 2.0, dbu, "ACTIVE.W1", "ACTIVE minimum width",  result)
    check_space(active, 2.5, dbu, "ACTIVE.S1", "ACTIVE minimum space",  result)

    # ---- NPLUS rules --------------------------------------------------------
    check_width(nplus,  2.0, dbu, "NPLUS.W1", "NPLUS minimum width",  result)
    check_space(nplus,  2.0, dbu, "NPLUS.S1", "NPLUS minimum space",  result)
    check_enclosure(nplus, active_nmos, 1.0, dbu,
                    "NPLUS.E1", "NPLUS enclosure of NMOS active", result)

    # ---- PPLUS rules --------------------------------------------------------
    check_width(pplus,  2.0, dbu, "PPLUS.W1", "PPLUS minimum width",  result)
    check_space(pplus,  2.0, dbu, "PPLUS.S1", "PPLUS minimum space",  result)
    check_enclosure(pplus, active_pmos, 1.0, dbu,
                    "PPLUS.E1", "PPLUS enclosure of PMOS active", result)

    # ---- POLY rules ---------------------------------------------------------
    check_width(poly,  1.0, dbu, "POLY.W1", "POLY minimum width",  result)
    check_space(poly,  2.0, dbu, "POLY.S1", "POLY minimum space",  result)

    # POLY.E1 – Gate poly extension beyond active
    _check_poly_extension(non_gate, 0.5, dbu, result)

    # POLY.SP1 – Routing poly to active spacing (poly that doesn't cross active)
    routing_poly = poly - poly.interacting(active)
    if not routing_poly.is_empty() and not active.is_empty():
        min_dbu = int(round(0.5 / dbu))
        sp_viol = routing_poly.edges().separation_check(active.edges(), min_dbu)
        if not sp_viol.is_empty():
            result.add("POLY.SP1", "Routing poly to active space < 0.5 μm")

    # ---- CONTACT rules ------------------------------------------------------
    check_width(contact,  1.2, dbu, "CONT.W1", "CONTACT minimum width", result)
    check_space(contact,  1.2, dbu, "CONT.S1", "CONTACT minimum space", result)
    check_enclosure(active, contact & active, 0.5, dbu,
                    "CONT.E1", "ACTIVE enclosure of contact", result)
    check_enclosure(poly,   contact & poly,   0.5, dbu,
                    "CONT.E2", "POLY enclosure of contact",   result)
    check_not_outside(contact, active + poly, "CONT.R1",
                      "CONTACT not inside ACTIVE or POLY", result)

    # ---- METAL1 rules -------------------------------------------------------
    check_width(metal1, 1.5, dbu, "MET1.W1", "METAL1 minimum width", result)
    check_space(metal1, 2.0, dbu, "MET1.S1", "METAL1 minimum space", result)
    check_enclosure(metal1, contact & metal1, 0.5, dbu,
                    "MET1.E1", "METAL1 enclosure of contact", result)
    check_not_outside(contact, metal1, "MET1.R1",
                      "CONTACT not covered by METAL1", result)

    # ---- VIA1 rules ---------------------------------------------------------
    check_width(via1, 1.5, dbu, "VIA1.W1", "VIA1 minimum width", result)
    check_space(via1, 1.5, dbu, "VIA1.S1", "VIA1 minimum space", result)
    check_enclosure(metal1, via1 & metal1, 0.5, dbu,
                    "VIA1.E1", "METAL1 enclosure of VIA1", result)
    check_enclosure(metal2, via1 & metal2, 0.5, dbu,
                    "VIA1.E2", "METAL2 enclosure of VIA1", result)
    check_not_outside(via1, metal1, "VIA1.R1", "VIA1 not inside METAL1", result)
    check_not_outside(via1, metal2, "VIA1.R2", "VIA1 not inside METAL2", result)

    # ---- METAL2 rules -------------------------------------------------------
    check_width(metal2, 2.0, dbu, "MET2.W1", "METAL2 minimum width", result)
    check_space(metal2, 2.5, dbu, "MET2.S1", "METAL2 minimum space", result)

    # ---- VIA2 rules ---------------------------------------------------------
    check_width(via2, 1.5, dbu, "VIA2.W1", "VIA2 minimum width", result)
    check_space(via2, 1.5, dbu, "VIA2.S1", "VIA2 minimum space", result)
    check_enclosure(metal2, via2 & metal2, 0.5, dbu,
                    "VIA2.E1", "METAL2 enclosure of VIA2", result)
    check_enclosure(metal3, via2 & metal3, 0.5, dbu,
                    "VIA2.E2", "METAL3 enclosure of VIA2", result)
    check_not_outside(via2, metal2, "VIA2.R1", "VIA2 not inside METAL2", result)
    check_not_outside(via2, metal3, "VIA2.R2", "VIA2 not inside METAL3", result)

    # ---- METAL3 rules -------------------------------------------------------
    check_width(metal3, 2.5, dbu, "MET3.W1", "METAL3 minimum width", result)
    check_space(metal3, 3.0, dbu, "MET3.S1", "METAL3 minimum space", result)

    # ---- OVERGLASS rules ----------------------------------------------------
    check_width(overglass, 40.0, dbu, "OVGLS.W1", "OVERGLASS minimum width",  result)
    check_space(overglass, 30.0, dbu, "OVGLS.S1", "OVERGLASS minimum space",  result)
    check_enclosure(metal3, overglass & metal3, 10.0, dbu,
                    "OVGLS.E1", "METAL3 enclosure of OVERGLASS", result)
    check_not_outside(overglass, metal3, "OVGLS.R1",
                      "OVERGLASS not inside METAL3", result)

    return result


# ---------------------------------------------------------------------------
# Regression driver
# ---------------------------------------------------------------------------

def run_regression(gds_dir: str, verbose: bool) -> int:
    pass_dir = os.path.join(gds_dir, "pass")
    fail_dir = os.path.join(gds_dir, "fail")
    total = pass_tests = fail_tests = 0
    errors = []

    header = "=" * 70
    print(header)
    print("  TR-1um Python DRC Regression")
    print(f"  GDS dir: {gds_dir}")
    print(header)

    # --- PASS cases (expect 0 violations) ------------------------------------
    print("\n--- PASS cases (expect 0 violations) ---")
    if os.path.isdir(pass_dir):
        for fname in sorted(os.listdir(pass_dir)):
            if not fname.endswith(".gds"):
                continue
            path = os.path.join(pass_dir, fname)
            result = run_drc(path)
            total += 1
            if result.count() == 0:
                print(f"  PASS  {fname}  (0 violations)")
                pass_tests += 1
            else:
                print(f"  FAIL  {fname}  ({result.count()} violations – expected 0)")
                if verbose:
                    for rid, msg in result.violations:
                        print(f"        [{rid}] {msg}")
                errors.append(f"{fname}: expected 0 violations, got {result.count()}")
                fail_tests += 1

    # --- FAIL cases (expect ≥ 1 violation) -----------------------------------
    print("\n--- FAIL cases (expect ≥ 1 violation) ---")
    if os.path.isdir(fail_dir):
        for fname in sorted(os.listdir(fail_dir)):
            if not fname.endswith(".gds"):
                continue
            path = os.path.join(fail_dir, fname)
            result = run_drc(path)
            total += 1
            if result.count() >= 1:
                rules = ", ".join(r for r, _ in result.violations)
                print(f"  PASS  {fname}  ({result.count()} violation(s): {rules})")
                pass_tests += 1
            else:
                print(f"  FAIL  {fname}  (0 violations – expected ≥ 1)")
                errors.append(f"{fname}: expected ≥ 1 violation, got 0")
                fail_tests += 1

    print(f"\n{header}")
    print(f"  Results: {pass_tests}/{total} passed,  {fail_tests} failed")
    print(header)

    if errors:
        print("\nFailures:")
        for msg in errors:
            print(f"  - {msg}")
        return 1
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="TR-1um Python DRC regression runner"
    )
    parser.add_argument(
        "--gds-dir",
        default=os.path.join(os.path.dirname(__file__), "gds"),
        help="Directory containing pass/ and fail/ subdirectories",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print individual violation messages for failing PASS cases",
    )
    args = parser.parse_args()

    sys.exit(run_regression(args.gds_dir, args.verbose))


if __name__ == "__main__":
    main()
