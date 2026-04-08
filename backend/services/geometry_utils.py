"""Geometric helper utilities for layout analysis."""

import math


def polygon_bbox(points: list[list[float]]) -> list[float]:
    """Return [x_min, y_min, x_max, y_max] bounding box."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def polygon_area(points: list[list[float]]) -> float:
    """Compute area using the shoelace formula. Returns absolute value."""
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


def polygon_perimeter(points: list[list[float]]) -> float:
    """Compute perimeter of a polygon."""
    n = len(points)
    if n < 2:
        return 0.0
    perimeter = 0.0
    for i in range(n):
        j = (i + 1) % n
        dx = points[j][0] - points[i][0]
        dy = points[j][1] - points[i][1]
        perimeter += math.sqrt(dx * dx + dy * dy)
    return perimeter


def polygon_centroid(points: list[list[float]]) -> list[float]:
    """Compute centroid of a polygon."""
    n = len(points)
    if n == 0:
        return [0.0, 0.0]
    cx = sum(p[0] for p in points) / n
    cy = sum(p[1] for p in points) / n
    return [cx, cy]


def polygons_overlap(points1: list[list[float]], points2: list[list[float]]) -> bool:
    """Check if the bounding boxes of two polygons overlap."""
    bb1 = polygon_bbox(points1)
    bb2 = polygon_bbox(points2)
    return bboxes_overlap(bb1, bb2)


def bboxes_overlap(bb1: list[float], bb2: list[float]) -> bool:
    """Check if two bounding boxes overlap. Each is [x_min, y_min, x_max, y_max]."""
    if bb1[2] <= bb2[0] or bb2[2] <= bb1[0]:
        return False
    if bb1[3] <= bb2[1] or bb2[3] <= bb1[1]:
        return False
    return True


def overlap_area(bbox1: list[float], bbox2: list[float]) -> float:
    """Compute the overlap area between two bounding boxes."""
    x_overlap = max(0, min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0]))
    y_overlap = max(0, min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1]))
    return x_overlap * y_overlap


def is_rectangular(points: list[list[float]], tolerance: float = 0.1) -> bool:
    """Check if a polygon is roughly rectangular.

    A polygon is rectangular if it has 4 vertices and all interior
    angles are approximately 90 degrees.
    """
    n = len(points)
    if n != 4:
        return False

    for i in range(4):
        p0 = points[(i - 1) % 4]
        p1 = points[i]
        p2 = points[(i + 1) % 4]
        v1 = [p0[0] - p1[0], p0[1] - p1[1]]
        v2 = [p2[0] - p1[0], p2[1] - p1[1]]
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
        if mag1 == 0 or mag2 == 0:
            return False
        cos_angle = dot / (mag1 * mag2)
        # cos(90) = 0, so |cos_angle| should be near 0
        if abs(cos_angle) > tolerance:
            return False
    return True


def bbox_dimensions(bbox: list[float]) -> tuple[float, float]:
    """Return (width, height) of a bounding box."""
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def aspect_ratio(points: list[list[float]]) -> float:
    """Return aspect ratio (longer / shorter) of a polygon's bounding box."""
    bb = polygon_bbox(points)
    w, h = bbox_dimensions(bb)
    if w == 0 or h == 0:
        return float("inf")
    return max(w, h) / min(w, h)


def distance_to_centroid_range(points: list[list[float]]) -> tuple[float, float]:
    """Compute the range of distances from all vertices to the centroid.

    Returns (min_distance, max_distance). Used for spiral inductor
    inner/outer radius detection.
    """
    centroid = polygon_centroid(points)
    cx, cy = centroid
    distances = [math.sqrt((p[0] - cx) ** 2 + (p[1] - cy) ** 2) for p in points]
    return (min(distances), max(distances))


def bbox_area_ratio(points: list[list[float]]) -> float:
    """Compute the ratio of polygon area to its bounding box area.

    Spiral shapes have lower ratios (due to hollow center),
    rectangles have ratios close to 1.
    """
    bbox = polygon_bbox(points)
    bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    if bbox_area == 0:
        return 0.0
    poly_area = polygon_area(points)
    return poly_area / bbox_area


def median_edge_length(points: list[list[float]]) -> float:
    """Compute the median length of polygon edges.

    Used for estimating line width in spiral inductors.
    """
    n = len(points)
    if n < 2:
        return 0.0
    edge_lengths = []
    for i in range(n):
        j = (i + 1) % n
        dx = points[j][0] - points[i][0]
        dy = points[j][1] - points[i][1]
        edge_lengths.append(math.sqrt(dx * dx + dy * dy))
    sorted_lengths = sorted(edge_lengths)
    return sorted_lengths[n // 2]
