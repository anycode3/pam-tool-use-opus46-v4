"""Layout writer service for generating GDS and DXF files from layout data."""

from __future__ import annotations

import gdstk
import ezdxf


def write_gds(layout_data: dict, output_path: str) -> None:
    """Write layout data to a GDS file.

    Args:
        layout_data: Dict with 'geometries' list.
        output_path: Path to write the GDS file.
    """
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    for geo in layout_data.get("geometries", []):
        points = geo.get("points", [])
        if len(points) < 3:
            continue
        layer = geo.get("layer", 0)
        datatype = geo.get("datatype", 0)
        polygon = gdstk.Polygon(points, layer=layer, datatype=datatype)
        cell.add(polygon)

    lib.write_gds(output_path)


def write_dxf(layout_data: dict, output_path: str) -> None:
    """Write layout data to a DXF file.

    Args:
        layout_data: Dict with 'geometries' list.
        output_path: Path to write the DXF file.
    """
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Create layers based on unique layer numbers
    created_layers = set()
    for geo in layout_data.get("geometries", []):
        layer_num = geo.get("layer", 0)
        layer_name = f"LAYER_{layer_num}"
        if layer_name not in created_layers:
            doc.layers.add(layer_name)
            created_layers.add(layer_name)

    for geo in layout_data.get("geometries", []):
        points = geo.get("points", [])
        if len(points) < 3:
            continue
        layer_num = geo.get("layer", 0)
        layer_name = f"LAYER_{layer_num}"
        # Add as closed polyline
        msp.add_lwpolyline(
            [(p[0], p[1]) for p in points],
            close=True,
            dxfattribs={"layer": layer_name},
        )

    doc.saveas(output_path)


def write_layout(layout_data: dict, output_path: str, file_type: str) -> None:
    """Write layout data to file in the specified format.

    Args:
        layout_data: Dict with 'geometries' list.
        output_path: Path to write the file.
        file_type: "gds" or "dxf".

    Raises:
        ValueError: If file_type is not supported.
    """
    if file_type == "gds":
        write_gds(layout_data, output_path)
    elif file_type == "dxf":
        write_dxf(layout_data, output_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
