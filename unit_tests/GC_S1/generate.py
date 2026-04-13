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

    rule_id   = spec["rule_id"]
    layer_num = spec["layer"]["number"]
    datatype  = spec["layer"]["datatype"]
    cases     = spec["cases"]

    out_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (base_dir / "generated")
    out_dir.mkdir(parents=True, exist_ok=True)

    dbu = 0.001  # 1nm database unit = 0.001um

    # 固定図形サイズ
    rect_width_um = 2.0

    for case in cases:
        name      = case["name"]
        space_um  = float(case["width_um"])   # YAMLの width_um を space として使う
        height_um = float(case["height_um"])

        layout = pya.Layout()
        layout.dbu = dbu

        top   = layout.create_cell(name)
        layer = layout.layer(layer_num, datatype)

        rect_w = um_to_dbu(rect_width_um, dbu)
        space  = um_to_dbu(space_um, dbu)
        height = um_to_dbu(height_um, dbu)

        # 左側矩形
        box1 = pya.Box(0, 0, rect_w, height)

        # 右側矩形（space を空けて配置）
        box2 = pya.Box(rect_w + space, 0, rect_w + space + rect_w, height)

        top.shapes(layer).insert(box1)
        top.shapes(layer).insert(box2)

        gds_path  = out_dir / f"{name}.gds"
        json_path = out_dir / f"{name}.json"

        layout.write(str(gds_path))

        meta = {
            "rule_id": rule_id,
            "case_name": name,
            "layer": {"number": layer_num, "datatype": datatype},
            "parameters": {
                "space_um": space_um,
                "height_um": height_um,
                "rect_width_um": rect_width_um,
            },
            "expected_violations": case["expected_violations"],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"Generated: {gds_path}")


if __name__ == "__main__":
    main()