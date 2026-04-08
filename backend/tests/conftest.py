import shutil
import tempfile
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import gdstk
import ezdxf

from main import app


@pytest.fixture
def client(tmp_storage):
    return TestClient(app)


@pytest.fixture
def tmp_storage(monkeypatch):
    """Create a temporary storage directory and patch config to use it."""
    tmp = Path(tempfile.mkdtemp())
    import config
    monkeypatch.setattr(config, "STORAGE_DIR", tmp)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_gds_path(tmp_path):
    """Generate a simple GDS file with known geometry for testing."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")
    rect1 = gdstk.rectangle((0, 0), (100, 50), layer=1, datatype=0)
    cell.add(rect1)
    rect2 = gdstk.rectangle((10, 10), (90, 40), layer=2, datatype=0)
    cell.add(rect2)
    poly = gdstk.rectangle((200, 0), (250, 10), layer=3, datatype=0)
    cell.add(poly)
    rect3 = gdstk.rectangle((0, 100), (30, 130), layer=1, datatype=0)
    cell.add(rect3)
    gds_path = tmp_path / "test.gds"
    lib.write_gds(str(gds_path))
    return gds_path


@pytest.fixture
def sample_dxf_path(tmp_path):
    """Generate a simple DXF file with known geometry for testing."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    doc.layers.add("LAYER1", color=1)
    doc.layers.add("LAYER2", color=2)
    doc.layers.add("LAYER3", color=3)
    msp.add_lwpolyline(
        [(0, 0), (100, 0), (100, 50), (0, 50)],
        close=True,
        dxfattribs={"layer": "LAYER1"},
    )
    msp.add_lwpolyline(
        [(10, 10), (90, 10), (90, 40), (10, 40)],
        close=True,
        dxfattribs={"layer": "LAYER2"},
    )
    msp.add_lwpolyline(
        [(200, 0), (250, 0), (250, 10), (200, 10)],
        close=True,
        dxfattribs={"layer": "LAYER3"},
    )
    dxf_path = tmp_path / "test.dxf"
    doc.saveas(str(dxf_path))
    return dxf_path


@pytest.fixture
def sample_gds_with_devices(tmp_path):
    """GDS with recognizable device patterns."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # Capacitor: overlapping ME1 and ME2 rectangles
    cell.add(gdstk.rectangle((0, 0), (50, 50), layer=1, datatype=0))    # ME1
    cell.add(gdstk.rectangle((5, 5), (45, 45), layer=2, datatype=0))    # ME2

    # Resistor: thin strip on TFR layer
    cell.add(gdstk.rectangle((100, 0), (150, 5), layer=3, datatype=0))  # TFR

    # PAD: overlapping on ME1, ME2, VA1
    cell.add(gdstk.rectangle((200, 200), (220, 220), layer=1, datatype=0))  # ME1
    cell.add(gdstk.rectangle((200, 200), (220, 220), layer=2, datatype=0))  # ME2
    cell.add(gdstk.rectangle((200, 200), (220, 220), layer=4, datatype=0))  # VA1

    # GND via: overlapping on GND, ME1, ME2, VA1
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=5, datatype=0))  # GND
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=1, datatype=0))  # ME1
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=2, datatype=0))  # ME2
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=4, datatype=0))  # VA1

    gds_path = tmp_path / "devices.gds"
    lib.write_gds(str(gds_path))
    return gds_path


def _generate_spiral_polygon(
    outer_radius: float = 50.0,
    inner_radius: float = 10.0,
    turns: int = 3,
    width: float = 5.0,
    spacing: float = 5.0,
) -> list[tuple[float, float]]:
    """Generate vertices for a square spiral inductor polygon.

    Creates a spiral shape by tracing along edges and winding inward.
    Uses a "comb" approach to create a valid, non-self-intersecting polygon
    with many vertices and low compactness (high perimeter-to-area ratio).

    Args:
        outer_radius: Half-width of outer square
        inner_radius: Half-width of inner square (center hole)
        turns: Number of spiral turns
        width: Width of each spiral arm
        spacing: Gap between spiral arms

    Returns:
        List of (x, y) vertices forming a spiral polygon.
    """
    points = []
    half_outer = outer_radius / 2
    half_inner = inner_radius / 2
    step = width + spacing

    # Create a "meander" or "comb" shape that mimics spiral characteristics:
    # - Many vertices
    # - Low compactness (high perimeter-to-area ratio)
    # - Non-self-intersecting

    # Build a serpentine/meander pattern
    # This has low compactness like a spiral but is a valid simple polygon

    arm_extent = half_outer
    segments_per_arm = 4  # More segments = smoother

    # Start from outer right-top corner, trace serpentine inward
    y_pos = arm_extent

    for turn in range(turns):
        # Top arm (right to left)
        x_start = arm_extent - turn * step
        x_end = -arm_extent + turn * step

        if x_start <= x_end:
            break

        # Add points along top arm
        for i in range(segments_per_arm + 1):
            x = x_start - i * (x_start - x_end) / segments_per_arm
            points.append((x, y_pos))

        # Move down
        y_pos = -arm_extent + turn * step + width
        if y_pos <= -arm_extent + turn * step:
            y_pos = -arm_extent + turn * step

        # Add points for the turn
        for i in range(segments_per_arm + 1):
            x = x_end + i * (x_start - x_end - step) / segments_per_arm
            points.append((x, y_pos))

        # Move down again
        y_next = y_pos - spacing
        if y_next < -arm_extent + (turn + 1) * step:
            y_next = -arm_extent + (turn + 1) * step

        # Continue for next segment
        y_pos = y_next

    # Add closing points to make a valid polygon
    # Add points back to start to close the polygon
    if len(points) > 2:
        # Simple close: add a few points to return to start
        first_x, first_y = points[0]
        last_x, last_y = points[-1]

        # Add intermediate points to avoid self-intersection
        points.append((last_x, first_y))
        points.append((first_x, first_y))

    # Ensure minimum vertices
    if len(points) < 8:
        # Generate a simple C-shape with many vertices
        points = []
        n_pts = 16
        for i in range(n_pts):
            angle = -math.pi / 2 + i * math.pi / (n_pts - 1)
            r = half_outer - (half_outer - half_inner) * i / n_pts
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            points.append((x, y))
        # Add return path
        for i in range(n_pts - 1, -1, -1):
            angle = -math.pi / 2 + i * math.pi / (n_pts - 1)
            r = half_outer - (half_outer - half_inner) * i / n_pts - width
            if r > 0:
                x = r * math.cos(angle)
                y = r * math.sin(angle)
                points.append((x, y))

    return points


@pytest.fixture
def sample_gds_with_inductor(tmp_path):
    """GDS with spiral inductor pattern for testing inductor recognition."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # Generate spiral polygon vertices
    spiral_points = _generate_spiral_polygon(
        outer_radius=100.0,
        inner_radius=20.0,
        turns=3,
        width=8.0,
        spacing=6.0,
    )

    # Add spiral on both ME1 and ME2 layers (they overlap)
    spiral_poly = gdstk.Polygon(spiral_points, layer=1, datatype=0)
    cell.add(spiral_poly)  # ME1

    # Create a slightly smaller spiral for ME2 (overlapping with ME1)
    spiral_points_me2 = _generate_spiral_polygon(
        outer_radius=95.0,
        inner_radius=25.0,
        turns=3,
        width=8.0,
        spacing=6.0,
    )
    spiral_poly_me2 = gdstk.Polygon(spiral_points_me2, layer=2, datatype=0)
    cell.add(spiral_poly_me2)  # ME2

    # Also add a capacitor for comparison (should not be confused with inductor)
    cell.add(gdstk.rectangle((200, 0), (250, 50), layer=1, datatype=0))  # ME1 cap
    cell.add(gdstk.rectangle((205, 5), (245, 45), layer=2, datatype=0))  # ME2 cap

    gds_path = tmp_path / "inductor.gds"
    lib.write_gds(str(gds_path))
    return gds_path