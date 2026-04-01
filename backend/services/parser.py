from pathlib import Path

from services.parser_gds import parse_gds
from services.parser_dxf import parse_dxf


def parse_layout(file_path: str) -> dict:
    """Parse a layout file (GDS or DXF) and return unified geometry data."""
    suffix = Path(file_path).suffix.lower()

    if suffix in (".gds", ".gds2", ".gdsii"):
        return parse_gds(file_path)
    elif suffix == ".dxf":
        return parse_dxf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
