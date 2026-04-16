#!/usr/bin/env python3
from pathlib import Path
import json
import yaml
import sys
import ast

import klayout.db as pya


def um_to_dbu(value_um: float, dbu: float) -> int:
    return round(value_um / dbu)


def eval_expr(expr):
    if isinstance(expr, (int, float)):
        return float(expr)

    node = ast.parse(str(expr), mode="eval")

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return float(n.value)
            raise ValueError(f"Unsupported constant: {n.value}")
        if isinstance(n, ast.Num):
            return float(n.n)
        if isinstance(n, ast.BinOp):
            left = _eval(n.left)
            right = _eval(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            if isinstance(n.op, ast.Div):
                return left / right
            raise ValueError(f"Unsupported operator: {type(n.op).__name__}")
        if isinstance(n, ast.UnaryOp):
            val = _eval(n.operand)
            if isinstance(n.op, ast.UAdd):
                return +val
            if isinstance(n.op, ast.USub):
                return -val
            raise ValueError(f"Unsupported unary operator: {type(n.op).__name__}")
        raise ValueError(f"Unsupported expression: {ast.dump(n)}")

    return float(_eval(node))


def parse_rect(rect):
    if not isinstance(rect, list) or len(rect) != 4:
        raise ValueError(f"Rect must be a list of 4 values: {rect}")
    x1 = eval_expr(rect[0])
    y1 = eval_expr(rect[1])
    x2 = eval_expr(rect[2])
    y2 = eval_expr(rect[3])
    return x1, y1, x2, y2


def normalize_rects(shape_value):
    """
    Accept both:
      AP: [0, 0, 10, 10]
    and:
      AP:
        - [0, 0, 10, 10]
        - [12, 0, 22, 10]
    Return a list of rects.
    """
    if not isinstance(shape_value, list):
        raise ValueError(f"Shape must be a list: {shape_value}")

    # single rectangle: [x1, y1, x2, y2]
    if len(shape_value) == 4 and not any(isinstance(v, list) for v in shape_value):
        return [shape_value]

    # multiple rectangles: [[...], [...]]
    if all(isinstance(v, list) for v in shape_value):
        return shape_value

    raise ValueError(f"Invalid shape format: {shape_value}")


def main():
    base_dir = Path(__file__).resolve().parent
    cases_file = base_dir / "cases.yaml"

    with open(cases_file, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    rule_id = spec["rule_id"]
    layers = spec["layers"]
    cases = spec["cases"]

    out_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (base_dir / "generated")
    out_dir.mkdir(parents=True, exist_ok=True)

    dbu = 0.001  # 1nm database unit = 0.001um

    for case in cases:
        name = case["name"]
        shapes = case["shapes"]

        layout = pya.Layout()
        layout.dbu = dbu

        top = layout.create_cell(name)

        layer_indices = {}
        for layer_name, layer_info in layers.items():
            layer_indices[layer_name] = layout.layer(layer_info["number"], layer_info["datatype"])

        shape_summary = {}

        for layer_name, shape_value in shapes.items():
            if layer_name not in layers:
                raise ValueError(f"Layer '{layer_name}' in case '{name}' is not defined in top-level layers")

            rects = normalize_rects(shape_value)
            parsed_rects = []

            for rect in rects:
                x1, y1, x2, y2 = parse_rect(rect)

                box = pya.Box(
                    um_to_dbu(x1, dbu),
                    um_to_dbu(y1, dbu),
                    um_to_dbu(x2, dbu),
                    um_to_dbu(y2, dbu),
                )
                top.shapes(layer_indices[layer_name]).insert(box)

                parsed_rects.append({
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                })

            shape_summary[layer_name] = parsed_rects

        gds_path = out_dir / f"{name}.gds"
        json_path = out_dir / f"{name}.json"

        layout.write(str(gds_path))

        meta = {
            "rule_id": rule_id,
            "case_name": name,
            "layers": layers,
            "parameters": {
                "shapes_um": shape_summary
            },
            "expected_violations": case["expected_violations"],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"Generated: {gds_path}")

    print(f"Done. Output directory: {out_dir}")


if __name__ == "__main__":
    main()
    