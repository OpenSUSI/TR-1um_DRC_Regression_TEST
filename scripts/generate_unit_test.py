#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import ast
import json
import sys

import klayout.db as pya
import yaml


DEFAULT_DBU = 0.001


def um_to_dbu(value_um: float, dbu: float) -> int:
    """Convert micrometers to database units."""
    return round(value_um / dbu)


def eval_expr(expr: object) -> float:
    """
    Safely evaluate a numeric expression.

    Supported:
        - int / float
        - +, -, *, /
        - unary + and -
        - expressions such as "30-6.95"
    """
    if isinstance(expr, (int, float)):
        return float(expr)

    node = ast.parse(str(expr), mode="eval")

    def _eval(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _eval(n.body)

        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return float(n.value)
            raise ValueError(f"unsupported constant: {n.value}")

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

            raise ValueError(f"unsupported operator: {type(n.op).__name__}")

        if isinstance(n, ast.UnaryOp):
            value = _eval(n.operand)

            if isinstance(n.op, ast.UAdd):
                return +value
            if isinstance(n.op, ast.USub):
                return -value

            raise ValueError(f"unsupported unary operator: {type(n.op).__name__}")

        raise ValueError(f"unsupported expression: {ast.dump(n)}")

    return float(_eval(node))


def parse_rect(rect: object) -> tuple[float, float, float, float]:
    """
    Parse a rectangle definition [x1, y1, x2, y2] in micrometers.
    """
    if not isinstance(rect, list) or len(rect) != 4:
        raise ValueError(f"rect must be a list of 4 values: {rect}")

    x1 = eval_expr(rect[0])
    y1 = eval_expr(rect[1])
    x2 = eval_expr(rect[2])
    y2 = eval_expr(rect[3])

    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"rect must satisfy x2>x1 and y2>y1: {rect}")

    return x1, y1, x2, y2


def normalize_shapes(shape_value: object) -> list[object]:
    """
    Normalize shape input into a list.

    Supported inputs:
        - single typed shape dict
        - single rect list [x1, y1, x2, y2]
        - list of typed shapes and/or rects
    """
    if isinstance(shape_value, dict):
        return [shape_value]

    if not isinstance(shape_value, list):
        raise ValueError(f"invalid shape specification: {shape_value}")

    if len(shape_value) == 4 and not any(
        isinstance(v, (list, dict)) for v in shape_value
    ):
        return [shape_value]

    if all(isinstance(v, (list, dict)) for v in shape_value):
        return shape_value

    raise ValueError(f"invalid shape format: {shape_value}")


def make_box(rect_um: tuple[float, float, float, float], dbu: float) -> pya.Box:
    """Create a KLayout box from a rectangle in micrometers."""
    x1, y1, x2, y2 = rect_um
    return pya.Box(
        um_to_dbu(x1, dbu),
        um_to_dbu(y1, dbu),
        um_to_dbu(x2, dbu),
        um_to_dbu(y2, dbu),
    )


def make_polygon(points_um: list[list[object]], dbu: float) -> pya.Polygon:
    """Create a KLayout polygon from point coordinates in micrometers."""
    points = [
        pya.Point(
            um_to_dbu(eval_expr(x), dbu),
            um_to_dbu(eval_expr(y), dbu),
        )
        for x, y in points_um
    ]
    return pya.Polygon(points)


def octagon_points_from_box(
    box_um: tuple[float, float, float, float],
    cut_um: float,
) -> list[list[float]]:
    """
    Generate octagon points by cutting the four corners of a box.
    """
    x1, y1, x2, y2 = box_um
    width = x2 - x1
    height = y2 - y1

    if cut_um <= 0:
        raise ValueError(f"cut must be positive: {cut_um}")
    if 2 * cut_um >= width:
        raise ValueError(f"cut too large for octagon width: cut={cut_um}, width={width}")
    if 2 * cut_um >= height:
        raise ValueError(
            f"cut too large for octagon height: cut={cut_um}, height={height}"
        )

    return [
        [x1 + cut_um, y1],
        [x2 - cut_um, y1],
        [x2, y1 + cut_um],
        [x2, y2 - cut_um],
        [x2 - cut_um, y2],
        [x1 + cut_um, y2],
        [x1, y2 - cut_um],
        [x1, y1 + cut_um],
    ]


def region_from_rect(shape: list[object], dbu: float) -> tuple[pya.Region, dict]:
    """Create a region and summary from a simple rectangle shape."""
    rect_um = parse_rect(shape)
    box = make_box(rect_um, dbu)

    summary = {
        "type": "box",
        "coords_um": {
            "x1": rect_um[0],
            "y1": rect_um[1],
            "x2": rect_um[2],
            "y2": rect_um[3],
        },
    }
    return pya.Region(box), summary


def region_from_polygon(shape: dict, dbu: float) -> tuple[pya.Region, dict]:
    """Create a region and summary from a polygon shape."""
    points = shape.get("points")
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError(f"polygon requires at least 3 points: {shape}")

    polygon = make_polygon(points, dbu)
    evaluated_points = [[eval_expr(x), eval_expr(y)] for x, y in points]

    summary = {
        "type": "polygon",
        "points_um": evaluated_points,
    }
    return pya.Region(polygon), summary


def region_from_octagon(shape: dict, dbu: float) -> tuple[pya.Region, dict]:
    """Create a region and summary from an octagon shape."""
    box_spec = shape.get("box")
    cut_um = eval_expr(shape.get("cut"))
    box_um = parse_rect(box_spec)
    points_um = octagon_points_from_box(box_um, cut_um)
    polygon = make_polygon(points_um, dbu)

    summary = {
        "type": "octagon",
        "box_um": {
            "x1": box_um[0],
            "y1": box_um[1],
            "x2": box_um[2],
            "y2": box_um[3],
        },
        "cut_um": cut_um,
        "points_um": points_um,
    }
    return pya.Region(polygon), summary


def region_from_donut(shape: dict, dbu: float) -> tuple[pya.Region, dict]:
    """Create a region and summary from a donut shape."""
    outer_spec = shape.get("outer")
    inner_spec = shape.get("inner")

    outer_um = parse_rect(outer_spec)
    inner_um = parse_rect(inner_spec)

    outer_width = outer_um[2] - outer_um[0]
    outer_height = outer_um[3] - outer_um[1]
    inner_width = inner_um[2] - inner_um[0]
    inner_height = inner_um[3] - inner_um[1]

    if inner_width >= outer_width or inner_height >= outer_height:
        raise ValueError(f"inner donut must be smaller than outer donut: {shape}")

    if not (
        outer_um[0] < inner_um[0]
        and outer_um[1] < inner_um[1]
        and inner_um[2] < outer_um[2]
        and inner_um[3] < outer_um[3]
    ):
        raise ValueError(
            f"inner donut box must be strictly inside outer donut box: {shape}"
        )

    outer_region = pya.Region(make_box(outer_um, dbu))
    inner_region = pya.Region(make_box(inner_um, dbu))
    ring = outer_region - inner_region

    summary = {
        "type": "donut",
        "outer_um": {
            "x1": outer_um[0],
            "y1": outer_um[1],
            "x2": outer_um[2],
            "y2": outer_um[3],
        },
        "inner_um": {
            "x1": inner_um[0],
            "y1": inner_um[1],
            "x2": inner_um[2],
            "y2": inner_um[3],
        },
    }
    return ring, summary


def region_from_shape(shape: object, dbu: float) -> tuple[pya.Region, dict]:
    """
    Create a KLayout region and summary dictionary from one shape definition.
    """
    if isinstance(shape, list):
        return region_from_rect(shape, dbu)

    if not isinstance(shape, dict):
        raise ValueError(f"unsupported shape type: {shape}")

    shape_type = shape.get("type")
    if not shape_type:
        raise ValueError(f"typed shape must have 'type': {shape}")

    if shape_type == "polygon":
        return region_from_polygon(shape, dbu)

    if shape_type == "octagon":
        return region_from_octagon(shape, dbu)

    if shape_type == "donut":
        return region_from_donut(shape, dbu)

    raise ValueError(f"unsupported shape type: {shape_type}")


def insert_region_to_layer(cell: pya.Cell, layer_index: int, region: pya.Region) -> None:
    """Insert all polygons from a region into a layout layer."""
    for polygon in region.each():
        cell.shapes(layer_index).insert(polygon)


def load_cases_file(cases_file: Path) -> dict:
    """Load and validate a cases.yaml file."""
    with cases_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"invalid YAML structure: {cases_file}")

    if "rule_id" not in data:
        raise ValueError(f"missing top-level 'rule_id' in {cases_file}")

    if "layers" not in data or not isinstance(data["layers"], dict):
        raise ValueError(f"missing or invalid 'layers' in {cases_file}")

    if "cases" not in data or not isinstance(data["cases"], list):
        raise ValueError(f"missing or invalid 'cases' in {cases_file}")

    return data


def build_layout_for_case(case_name: str, layers: dict, shapes: dict, dbu: float) -> tuple[pya.Layout, dict]:
    """
    Build one testcase layout and return:
        - KLayout Layout
        - shape summary metadata
    """
    layout = pya.Layout()
    layout.dbu = dbu

    top_cell = layout.create_cell(case_name)

    layer_indices: dict[str, int] = {}
    for layer_name, layer_info in layers.items():
        layer_number = layer_info["number"]
        layer_datatype = layer_info["datatype"]
        layer_indices[layer_name] = layout.layer(layer_number, layer_datatype)

    shape_summary: dict[str, list[dict]] = {}

    for layer_name, shape_value in shapes.items():
        if layer_name not in layers:
            raise ValueError(
                f"layer '{layer_name}' in case '{case_name}' is not defined in top-level layers"
            )

        normalized_shapes = normalize_shapes(shape_value)
        parsed_shapes: list[dict] = []

        for shape in normalized_shapes:
            region, summary = region_from_shape(shape, dbu)
            insert_region_to_layer(top_cell, layer_indices[layer_name], region)
            parsed_shapes.append(summary)

        shape_summary[layer_name] = parsed_shapes

    return layout, shape_summary


def write_case_outputs(
    out_dir: Path,
    rule_id: str,
    case: dict,
    layers: dict,
    layout: pya.Layout,
    shape_summary: dict,
) -> None:
    """Write GDS and JSON metadata for one testcase."""
    case_name = str(case["name"])
    gds_path = out_dir / f"{case_name}.gds"
    json_path = out_dir / f"{case_name}.json"

    layout.write(str(gds_path))

    metadata = {
        "rule_id": rule_id,
        "case_name": case_name,
        "layers": layers,
        "parameters": {
            "shapes_um": shape_summary,
        },
        "expected_violations": int(case.get("expected_violations", 0)),
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Generated       : {gds_path}")


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        print("Usage: python3 scripts/generate_unit_test.py <cases.yaml> [output_dir]")
        sys.exit(1)

    cases_file = Path(sys.argv[1]).resolve()
    if not cases_file.exists():
        print(f"Error: cases file not found: {cases_file}")
        sys.exit(1)

    out_dir = (
        Path(sys.argv[2]).resolve()
        if len(sys.argv) == 3
        else cases_file.parent / "generated"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        spec = load_cases_file(cases_file)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    rule_id = str(spec["rule_id"]).strip()
    layers = spec["layers"]
    cases = spec["cases"]
    dbu = DEFAULT_DBU

    print(f"Cases file      : {cases_file}")
    print(f"Output dir      : {out_dir}")
    print(f"Rule ID         : {rule_id}")
    print(f"DBU             : {dbu}")

    for case in cases:
        case_name = str(case["name"]).strip()
        shapes = case.get("shapes", {})

        if not case_name:
            print("Error: case without name")
            sys.exit(1)

        if not isinstance(shapes, dict):
            print(f"Error: 'shapes' must be a dictionary in case '{case_name}'")
            sys.exit(1)

        try:
            layout, shape_summary = build_layout_for_case(case_name, layers, shapes, dbu)
            write_case_outputs(out_dir, rule_id, case, layers, layout, shape_summary)
        except Exception as exc:
            print(f"Error: failed to generate case '{case_name}': {exc}")
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()