#!/usr/bin/env python3
"""
generate_tests.py – Generate GDS test layouts for TR-1um DRC regression.

Requires the KLayout Python package (klayout.db):
    pip install klayout

Outputs
-------
tests/gds/pass/  – layouts that must produce zero DRC violations
tests/gds/fail/  – layouts that must produce ≥ 1 DRC violation each

Each file name encodes the test case and (for fail cases) the rule expected
to be violated, e.g. ``fail_NWELL_W1.gds``.

Run
---
    python tests/generate_tests.py
"""

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
# TR-1um layer map  (layer number, datatype)
# ---------------------------------------------------------------------------
LAYERS = {
    "nwell":     (1,  0),
    "active":    (2,  0),
    "nplus":     (3,  0),
    "pplus":     (4,  0),
    "poly":      (5,  0),
    "contact":   (6,  0),
    "metal1":    (7,  0),
    "via1":      (8,  0),
    "metal2":    (9,  0),
    "via2":      (10, 0),
    "metal3":    (11, 0),
    "overglass": (12, 0),
}

# Scale factor: KLayout internal units are nm when dbu=0.001 um
DBU = 0.001          # database unit in μm  (1 nm)
UM  = 1 / DBU        # 1 μm in DB units


def um(val: float) -> int:
    """Convert μm to database units."""
    return int(round(val * UM))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def new_layout(cell_name: str = "TOP") -> tuple:
    """Return (layout, top_cell, layer_dict)."""
    layout = db.Layout()
    layout.dbu = DBU
    top = layout.create_cell(cell_name)
    layers = {
        name: layout.layer(*lp) for name, lp in LAYERS.items()
    }
    return layout, top, layers


def box(x0, y0, x1, y1) -> db.Box:
    """Create a Box from μm coordinates."""
    return db.Box(um(x0), um(y0), um(x1), um(y1))


def save(layout: db.Layout, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    layout.write(path)
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# PASS test cases  (no DRC violations expected)
# ---------------------------------------------------------------------------

def make_pass_nmos(out_dir: str) -> None:
    """Minimal legal NMOS transistor.

    Layout (all dimensions in μm):

    Active  : (0, 0) – (8, 3)          width=8, height=3 > 2.0 ✓
    NPLUS   : (-1,-1) – (9, 4)         encloses active by 1.0 μm ✓
    Gate poly: (3.5,-0.5) – (4.5, 3.5) width=1.0 μm, ext=0.5 μm ✓
    Src cont : (0.5, 0.9) – (1.7, 2.1) 1.2×1.2 μm, clear of poly ✓
    Drn cont : (5.3, 0.9) – (6.5, 2.1) 1.2×1.2 μm, clear of poly ✓
    Src M1   : (0.0, 0.4) – (2.2, 2.6) encloses src cont by 0.5 μm ✓
    Drn M1   : (4.8, 0.4) – (7.0, 2.6) encloses drn cont by 0.5 μm ✓
    M1 space : 4.8 – 2.2 = 2.6 μm > 2.0 μm ✓
    Cont space: 5.3 – 1.7 = 3.6 μm > 1.2 μm ✓
    """
    layout, top, L = new_layout()
    # Active 8×3 μm
    top.shapes(L["active"]).insert(box(0, 0, 8, 3))
    # NPLUS enclosing active by 1 μm
    top.shapes(L["nplus"]).insert(box(-1, -1, 9, 4))
    # Poly gate 1 μm wide, 0.5 μm extension beyond active top/bottom
    top.shapes(L["poly"]).insert(box(3.5, -0.5, 4.5, 3.5))
    # Source contact: 1.2×1.2 μm in source region, 0.5 μm from all active edges
    top.shapes(L["contact"]).insert(box(0.5, 0.9, 1.7, 2.1))
    # Drain contact: 1.2×1.2 μm in drain region, 0.5 μm from all active edges
    top.shapes(L["contact"]).insert(box(5.3, 0.9, 6.5, 2.1))
    # Metal1 enclosing source contact by 0.5 μm
    top.shapes(L["metal1"]).insert(box(0.0, 0.4, 2.2, 2.6))
    # Metal1 enclosing drain contact by 0.5 μm (2.6 μm gap from source metal)
    top.shapes(L["metal1"]).insert(box(4.8, 0.4, 7.0, 2.6))
    save(layout, os.path.join(out_dir, "pass_nmos.gds"))


def make_pass_metal_stack(out_dir: str) -> None:
    """Legal M1→Via1→M2→Via2→M3 stack."""
    layout, top, L = new_layout()
    # Metal1 10×3 μm
    top.shapes(L["metal1"]).insert(box(0, 0, 10, 3))
    # Via1 (1.5×1.5) with 0.5 μm enclosure in Metal1
    top.shapes(L["via1"]).insert(box(0.5, 0.75, 2.0, 2.25))
    # Metal2 enclosing via1 by 0.5 μm, min width 2 μm
    top.shapes(L["metal2"]).insert(box(0, 0.25, 10, 2.75))
    # Via2 (1.5×1.5) with 0.5 μm enclosure in Metal2
    top.shapes(L["via2"]).insert(box(0.5, 0.75, 2.0, 2.25))
    # Metal3 enclosing via2 by 0.5 μm, min width 2.5 μm
    top.shapes(L["metal3"]).insert(box(0, 0.25, 10, 2.75))
    save(layout, os.path.join(out_dir, "pass_metal_stack.gds"))


def make_pass_pad(out_dir: str) -> None:
    """Legal bond pad (overglass opening inside Metal3)."""
    layout, top, L = new_layout()
    # Metal3 60×60 μm
    top.shapes(L["metal3"]).insert(box(0, 0, 60, 60))
    # Overglass opening 40×40 μm, 10 μm from Metal3 edge
    top.shapes(L["overglass"]).insert(box(10, 10, 50, 50))
    save(layout, os.path.join(out_dir, "pass_pad.gds"))


# ---------------------------------------------------------------------------
# FAIL test cases  (each must trigger the named rule violation)
# ---------------------------------------------------------------------------

def make_fail_nwell_w1(out_dir: str) -> None:
    """NWELL.W1 – NWELL width 2.0 μm < 3.0 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["nwell"]).insert(box(0, 0, 2.0, 10))   # width = 2.0 μm < 3.0
    save(layout, os.path.join(out_dir, "fail_NWELL_W1.gds"))


def make_fail_nwell_s1(out_dir: str) -> None:
    """NWELL.S1 – NWELL spacing 3.0 μm < 5.0 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["nwell"]).insert(box(0, 0, 5, 10))
    top.shapes(L["nwell"]).insert(box(8, 0, 13, 10))   # space = 3.0 μm < 5.0
    save(layout, os.path.join(out_dir, "fail_NWELL_S1.gds"))


def make_fail_active_w1(out_dir: str) -> None:
    """ACTIVE.W1 – Active width 1.0 μm < 2.0 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["active"]).insert(box(0, 0, 1.0, 5))   # width = 1.0 μm < 2.0
    save(layout, os.path.join(out_dir, "fail_ACTIVE_W1.gds"))


def make_fail_active_s1(out_dir: str) -> None:
    """ACTIVE.S1 – Active spacing 1.5 μm < 2.5 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["active"]).insert(box(0, 0, 4, 4))
    top.shapes(L["active"]).insert(box(5.5, 0, 9.5, 4))  # space = 1.5 μm < 2.5
    save(layout, os.path.join(out_dir, "fail_ACTIVE_S1.gds"))


def make_fail_poly_w1(out_dir: str) -> None:
    """POLY.W1 – Poly width 0.8 μm < 1.0 μm minimum (gate too narrow)."""
    layout, top, L = new_layout()
    top.shapes(L["active"]).insert(box(0, 0, 4, 4))
    top.shapes(L["nplus"]).insert(box(-1, -1, 5, 5))
    top.shapes(L["poly"]).insert(box(1.5, -0.5, 2.3, 4.5))  # width = 0.8 μm < 1.0
    save(layout, os.path.join(out_dir, "fail_POLY_W1.gds"))


def make_fail_poly_s1(out_dir: str) -> None:
    """POLY.S1 – Poly to poly spacing 1.0 μm < 2.0 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["poly"]).insert(box(0, 0, 1, 5))
    top.shapes(L["poly"]).insert(box(2, 0, 3, 5))   # space = 1.0 μm < 2.0
    save(layout, os.path.join(out_dir, "fail_POLY_S1.gds"))


def make_fail_contact_s1(out_dir: str) -> None:
    """CONT.S1 – Contact to contact spacing 0.8 μm < 1.2 μm minimum."""
    layout, top, L = new_layout()
    # Two contacts with 0.8 μm gap, both inside active
    top.shapes(L["active"]).insert(box(-1, -1, 5, 5))
    top.shapes(L["nplus"]).insert(box(-2, -2, 6, 6))
    top.shapes(L["contact"]).insert(box(0, 0, 1.2, 1.2))
    top.shapes(L["contact"]).insert(box(2.0, 0, 3.2, 1.2))   # space = 0.8 μm < 1.2
    top.shapes(L["metal1"]).insert(box(-0.5, -0.5, 3.7, 1.7))
    save(layout, os.path.join(out_dir, "fail_CONT_S1.gds"))


def make_fail_cont_r1(out_dir: str) -> None:
    """CONT.R1 – Contact outside active and poly."""
    layout, top, L = new_layout()
    # Contact placed in open field (not in active or poly)
    top.shapes(L["contact"]).insert(box(5, 5, 6.2, 6.2))
    top.shapes(L["metal1"]).insert(box(4.5, 4.5, 6.7, 6.7))
    save(layout, os.path.join(out_dir, "fail_CONT_R1.gds"))


def make_fail_metal1_w1(out_dir: str) -> None:
    """MET1.W1 – Metal1 width 1.0 μm < 1.5 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["metal1"]).insert(box(0, 0, 1.0, 10))   # width = 1.0 μm < 1.5
    save(layout, os.path.join(out_dir, "fail_MET1_W1.gds"))


def make_fail_metal1_s1(out_dir: str) -> None:
    """MET1.S1 – Metal1 spacing 1.0 μm < 2.0 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["metal1"]).insert(box(0, 0, 3, 5))
    top.shapes(L["metal1"]).insert(box(4, 0, 7, 5))   # space = 1.0 μm < 2.0
    save(layout, os.path.join(out_dir, "fail_MET1_S1.gds"))


def make_fail_via1_r1(out_dir: str) -> None:
    """VIA1.R1 – Via1 not inside Metal1."""
    layout, top, L = new_layout()
    # Via1 completely outside Metal1
    top.shapes(L["via1"]).insert(box(10, 10, 11.5, 11.5))
    top.shapes(L["metal2"]).insert(box(9.5, 9.5, 12, 12))
    save(layout, os.path.join(out_dir, "fail_VIA1_R1.gds"))


def make_fail_metal2_w1(out_dir: str) -> None:
    """MET2.W1 – Metal2 width 1.5 μm < 2.0 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["metal2"]).insert(box(0, 0, 1.5, 10))   # width = 1.5 μm < 2.0
    save(layout, os.path.join(out_dir, "fail_MET2_W1.gds"))


def make_fail_metal3_w1(out_dir: str) -> None:
    """MET3.W1 – Metal3 width 2.0 μm < 2.5 μm minimum."""
    layout, top, L = new_layout()
    top.shapes(L["metal3"]).insert(box(0, 0, 2.0, 10))   # width = 2.0 μm < 2.5
    save(layout, os.path.join(out_dir, "fail_MET3_W1.gds"))


def make_fail_poly_e1(out_dir: str) -> None:
    """POLY.E1 – Gate poly extension beyond active only 0.3 μm < 0.5 μm."""
    layout, top, L = new_layout()
    top.shapes(L["active"]).insert(box(0, 0, 4, 4))
    top.shapes(L["nplus"]).insert(box(-1, -1, 5, 5))
    # Poly extends only 0.3 μm beyond active (top and bottom) → POLY.E1 violation
    top.shapes(L["poly"]).insert(box(1.5, -0.3, 2.5, 4.3))
    save(layout, os.path.join(out_dir, "fail_POLY_E1.gds"))


def make_fail_ovgls_r1(out_dir: str) -> None:
    """OVGLS.R1 – Overglass opening not inside Metal3."""
    layout, top, L = new_layout()
    top.shapes(L["overglass"]).insert(box(0, 0, 50, 50))   # no Metal3 at all
    save(layout, os.path.join(out_dir, "fail_OVGLS_R1.gds"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pass_dir = os.path.join(script_dir, "gds", "pass")
    fail_dir = os.path.join(script_dir, "gds", "fail")

    print("Generating PASS test cases …")
    make_pass_nmos(pass_dir)
    make_pass_metal_stack(pass_dir)
    make_pass_pad(pass_dir)

    print("\nGenerating FAIL test cases …")
    make_fail_nwell_w1(fail_dir)
    make_fail_nwell_s1(fail_dir)
    make_fail_active_w1(fail_dir)
    make_fail_active_s1(fail_dir)
    make_fail_poly_w1(fail_dir)
    make_fail_poly_s1(fail_dir)
    make_fail_contact_s1(fail_dir)
    make_fail_cont_r1(fail_dir)
    make_fail_metal1_w1(fail_dir)
    make_fail_metal1_s1(fail_dir)
    make_fail_via1_r1(fail_dir)
    make_fail_metal2_w1(fail_dir)
    make_fail_metal3_w1(fail_dir)
    make_fail_ovgls_r1(fail_dir)
    make_fail_poly_e1(fail_dir)

    print("\nDone.  Test GDS files written to tests/gds/")


if __name__ == "__main__":
    main()
