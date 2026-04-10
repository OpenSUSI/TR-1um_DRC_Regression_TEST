#!/usr/bin/env python3
from pathlib import Path
import json
import yaml
import sys

import klayout.db as pya

def um_to_dbu(value_um: float, dbu: float) -> int:
    return round(value_um / dbu)

def main():
    base_dir = Path(__file__).resolve().parent
    cases_file = base_dir / "cases.yaml"

    with open(cases_file, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    rule_id     = spec["rule_id"]
    layer_num   = spec["layer"]["number"]
    datatype    = spec["layer"]["datatype"]
    cases       = spec["cases"]

    out_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (base_dir / "generated")
    out_dir.mkdir(parents=True, exist_ok=True)

    dbu = 0.001  # 1nm database unit = 0.001um

    for case in cases:
        name        = case["name"]
        width_um    = float(case["width_um"])
        height_um   = float(case["height_um"])

        layout = pya.Layout()
        layout.dbu = dbu

        top     = layout.create_cell(name)
        layer   = layout.layer(layer_num, datatype)

        w = um_to_dbu(width_um, dbu)
        h = um_to_dbu(height_um, dbu)

        box = pya.Box(0, 0, w, h)
        top.shapes(layer).insert(box)

        gds_path = out_dir / f"{name}.gds"
        json_path = out_dir / f"{name}.json"

        layout.write(str(gds_path))

        meta = {
            "rule_id": rule_id,
            "case_name": name,
            "layer": {"number": layer_num, "datatype": datatype},
            "parameters": {
                "width_um": width_um,
                "height_um": height_um,
            },
            "expected_violations": case["expected_violations"],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"Generated: {gds_path}")


if __name__ == "__main__":
    main()