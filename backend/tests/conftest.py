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


@pytest.fixture
def sample_gds_with_separate_spiral(tmp_path):
    """GDS with spiral inductor represented as separate rectangles (multi-polygon)."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # Generate a 3-turn square spiral using separate rectangles
    center_x, center_y = 50, 50
    width = 8  # Arm width
    turns = 3

    for turn in range(turns):
        size = 90 - turn * 20  # Decreasing size for each turn
        half = size / 2

        # Four arms: top, right, bottom, left
        # Top arm
        cell.add(gdstk.rectangle(
            (center_x - half, center_y + half - width),
            (center_x + half, center_y + half),
            layer=1, datatype=0
        ))
        cell.add(gdstk.rectangle(
            (center_x - half, center_y + half - width),
            (center_x + half, center_y + half),
            layer=2, datatype=0
        ))

        # Right arm
        cell.add(gdstk.rectangle(
            (center_x + half - width, center_y - half),
            (center_x + half, center_y + half),
            layer=1, datatype=0
        ))
        cell.add(gdstk.rectangle(
            (center_x + half - width, center_y - half),
            (center_x + half, center_y + half),
            layer=2, datatype=0
        ))

        # Bottom arm
        cell.add(gdstk.rectangle(
            (center_x - half, center_y - half),
            (center_x + half, center_y - half + width),
            layer=1, datatype=0
        ))
        cell.add(gdstk.rectangle(
            (center_x - half, center_y - half),
            (center_x + half, center_y - half + width),
            layer=2, datatype=0
        ))

        # Left arm
        cell.add(gdstk.rectangle(
            (center_x - half, center_y - half),
            (center_x - half + width, center_y + half),
            layer=1, datatype=0
        ))
        cell.add(gdstk.rectangle(
            (center_x - half, center_y - half),
            (center_x - half + width, center_y + half),
            layer=2, datatype=0
        ))

    # Add a separate capacitor (should not be confused with inductor)
    cell.add(gdstk.rectangle((150, 0), (200, 50), layer=1, datatype=0))
    cell.add(gdstk.rectangle((155, 5), (195, 45), layer=2, datatype=0))

    gds_path = tmp_path / "separate_spiral.gds"
    lib.write_gds(str(gds_path))
    return gds_path


def _generate_closed_spiral_polygon(
    center: tuple[float, float] = (0.0, 0.0),
    outer_size: float = 100.0,
    inner_size: float = 20.0,
    turns: int = 3,
    line_width: float = 8.0,
) -> list[tuple[float, float]]:
    """Generate a closed square spiral polygon.

    Creates a continuous spiral path from outer to inner, then closes.

    Args:
        center: (x, y) center of spiral
        outer_size: Outer dimension (full size, not half)
        inner_size: Inner dimension (full size, not half)
        turns: Number of turns
        line_width: Width of spiral line

    Returns:
        List of (x, y) vertices forming a closed spiral polygon.
    """
    cx, cy = center
    half_outer = outer_size / 2
    half_inner = inner_size / 2
    step = line_width * 1.2  # Spacing between turns

    points = []

    # Generate spiral path starting from outer edge
    # We'll create a continuous path that spirals inward

    # Starting position (top-right outer corner)
    x = cx + half_outer
    y = cy + half_outer
    points.append((x, y))

    for turn in range(turns):
        current_half = half_outer - turn * step

        if current_half <= half_inner:
            # Final segment to center
            points.append((cx + half_inner, cy + half_inner))
            break

        # Top edge: right to left
        points.append((cx - current_half, cy + current_half))

        # Left edge: top to bottom
        points.append((cx - current_half, cy - current_half))

        # Bottom edge: left to right
        points.append((cx + current_half, cy - current_half))

        # Right edge: bottom to top (but stop short for next turn)
        next_half = current_half - step
        if next_half > half_inner:
            points.append((cx + next_half, cy - current_half))

    # Now spiral inward (reverse direction)
    for turn in range(turns - 1, -1, -1):
        current_half = half_outer - turn * step
        next_half = current_half - step

        if next_half <= half_inner:
            # Close at center
            points.append((cx, cy))
            break

        # Bottom edge: right to left (inner)
        points.append((cx + next_half, cy - next_half))

        # Left edge: bottom to top (inner)
        points.append((cx - next_half, cy - next_half))

        # Top edge: left to right (inner)
        points.append((cx - next_half, cy + next_half))

        # Right edge: top to bottom (connecting to next outer)
        if turn > 0:
            connect_half = current_half - step
            points.append((cx + connect_half, cy + next_half))

    return points


@pytest.fixture
def sample_gds_with_me2_only_inductor(tmp_path):
    """GDS with ME2-only closed spiral inductor.

    ME2层有完整的闭合螺旋，ME1在电感区域外或没有。
    用于测试仅基于ME2检测电感的可行性。
    """
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # ME2 closed spiral (centered at 50, 50)
    me2_spiral_points = _generate_closed_spiral_polygon(
        center=(50.0, 50.0),
        outer_size=80.0,
        inner_size=15.0,
        turns=3,
        line_width=8.0,
    )

    me2_poly = gdstk.Polygon(me2_spiral_points, layer=2, datatype=0)
    cell.add(me2_poly)

    # Add a separate capacitor far from the inductor (should not be confused)
    cell.add(gdstk.rectangle((150, 0), (200, 50), layer=1, datatype=0))  # ME1 cap
    cell.add(gdstk.rectangle((155, 5), (195, 45), layer=2, datatype=0))  # ME2 cap

    gds_path = tmp_path / "me2_only_inductor.gds"
    lib.write_gds(str(gds_path))
    return gds_path


@pytest.fixture
def sample_gds_with_proper_inductor(tmp_path):
    """GDS with proper ME1+ME2 inductor structure.

    ME2有闭合螺旋，ME1有对应的多边形（在电感区域内）。
    用于测试ME1-ME2空间关系分析。
    """
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # ME2 closed spiral
    me2_spiral_points = _generate_closed_spiral_polygon(
        center=(50.0, 50.0),
        outer_size=80.0,
        inner_size=15.0,
        turns=3,
        line_width=8.0,
    )
    me2_poly = gdstk.Polygon(me2_spiral_points, layer=2, datatype=0)
    cell.add(me2_poly)

    # ME1: Add rectangles that correspond to spiral arms (inside inductor region)
    # These represent the ME1 layer that connects to ME2 spiral
    center_x, center_y = 50.0, 50.0

    # Add 4 ME1 rectangles at different positions in the spiral region
    me1_positions = [
        (center_x - 30, center_y + 30, center_x + 30, center_y + 38),  # Top arm
        (center_x + 30, center_y - 30, center_x + 38, center_y + 30),  # Right arm
        (center_x - 30, center_y - 38, center_x + 30, center_y - 30),  # Bottom arm
        (center_x - 38, center_y - 30, center_x - 30, center_y + 30),  # Left arm
    ]

    for x1, y1, x2, y2 in me1_positions:
        cell.add(gdstk.rectangle((x1, y1), (x2, y2), layer=1, datatype=0))

    # Add a separate capacitor far from the inductor
    cell.add(gdstk.rectangle((150, 0), (200, 50), layer=1, datatype=0))  # ME1 cap
    cell.add(gdstk.rectangle((155, 5), (195, 45), layer=2, datatype=0))  # ME2 cap

    gds_path = tmp_path / "proper_inductor.gds"
    lib.write_gds(str(gds_path))
    return gds_path


@pytest.fixture
def sample_gds_with_inductor_and_noise(tmp_path):
    """GDS with inductor plus nearby independent ME1 rectangles (noise).

    电感附近有独立的ME1多边形（不是电感的一部分）。
    用于测试能否正确区分。
    """
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # ME2 closed spiral inductor
    me2_spiral_points = _generate_closed_spiral_polygon(
        center=(50.0, 50.0),
        outer_size=80.0,
        inner_size=15.0,
        turns=3,
        line_width=8.0,
    )
    me2_poly = gdstk.Polygon(me2_spiral_points, layer=2, datatype=0)
    cell.add(me2_poly)

    # ME1: Add rectangles that ARE part of the inductor structure
    center_x, center_y = 50.0, 50.0
    me1_positions = [
        (center_x - 30, center_y + 30, center_x + 30, center_y + 38),
        (center_x + 30, center_y - 30, center_x + 38, center_y + 30),
        (center_x - 30, center_y - 38, center_x + 30, center_y - 30),
        (center_x - 38, center_y - 30, center_x - 30, center_y + 30),
    ]
    for x1, y1, x2, y2 in me1_positions:
        cell.add(gdstk.rectangle((x1, y1), (x2, y2), layer=1, datatype=0))

    # NOISE: Add independent ME1 rectangles far from inductor (not part of inductor)
    # These should NOT be confused as being part of the inductor
    noise_positions = [
        (200, 200, 230, 215),  # Far away in upper right
        (10, 200, 40, 215),    # Far away in upper left
        (200, 10, 230, 25),    # Far away in lower right
    ]
    for x1, y1, x2, y2 in noise_positions:
        cell.add(gdstk.rectangle((x1, y1), (x2, y2), layer=1, datatype=0))

    # Add a separate capacitor
    cell.add(gdstk.rectangle((150, 0), (200, 50), layer=1, datatype=0))
    cell.add(gdstk.rectangle((155, 5), (195, 45), layer=2, datatype=0))

    gds_path = tmp_path / "inductor_with_noise.gds"
    lib.write_gds(str(gds_path))
    return gds_path


@pytest.fixture
def sample_gds_mixed_devices(tmp_path):
    """GDS with inductor, capacitor, resistor, PAD, and GND via.

    混合版图，测试所有器件类型能被正确区分。
    """
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # === INDUCTOR (left side) ===
    me2_spiral_points = _generate_closed_spiral_polygon(
        center=(40.0, 40.0),
        outer_size=60.0,
        inner_size=12.0,
        turns=2,
        line_width=6.0,
    )
    cell.add(gdstk.Polygon(me2_spiral_points, layer=2, datatype=0))

    # ME1 for inductor
    for x1, y1, x2, y2 in [
        (20, 55, 60, 62),  # Top
        (52, 20, 60, 60),  # Right
        (20, 18, 60, 25),   # Bottom
        (18, 20, 25, 60),   # Left
    ]:
        cell.add(gdstk.rectangle((x1, y1), (x2, y2), layer=1, datatype=0))

    # === CAPACITOR (center) ===
    cell.add(gdstk.rectangle((100, 30), (150, 70), layer=1, datatype=0))  # ME1
    cell.add(gdstk.rectangle((105, 35), (145, 65), layer=2, datatype=0))  # ME2

    # === RESISTOR (right side) ===
    cell.add(gdstk.rectangle((200, 40), (260, 48), layer=3, datatype=0))  # TFR

    # === PAD (upper right) ===
    cell.add(gdstk.rectangle((180, 150), (200, 170), layer=1, datatype=0))  # ME1
    cell.add(gdstk.rectangle((180, 150), (200, 170), layer=2, datatype=0))  # ME2
    cell.add(gdstk.rectangle((185, 155), (195, 165), layer=4, datatype=0))  # VA1

    # === GND VIA (upper right, different location) ===
    cell.add(gdstk.rectangle((220, 150), (230, 160), layer=5, datatype=0))  # GND
    cell.add(gdstk.rectangle((220, 150), (230, 160), layer=1, datatype=0))  # ME1
    cell.add(gdstk.rectangle((220, 150), (230, 160), layer=2, datatype=0))  # ME2
    cell.add(gdstk.rectangle((222, 152), (228, 158), layer=4, datatype=0))  # VA1

    gds_path = tmp_path / "mixed_devices.gds"
    lib.write_gds(str(gds_path))
    return gds_path