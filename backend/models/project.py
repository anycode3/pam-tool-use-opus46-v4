from pydantic import BaseModel


class Bounds(BaseModel):
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class LayerInfo(BaseModel):
    layer: int
    datatype: int
    name: str
    polygon_count: int


class Geometry(BaseModel):
    id: str
    type: str
    layer: int
    datatype: int
    points: list[list[float]]
    properties: dict = {}


class LayoutData(BaseModel):
    bounds: Bounds
    layers: list[LayerInfo]
    geometries: list[Geometry]


class ProjectInfo(BaseModel):
    id: str
    name: str
    file_type: str
    file_size: int
    created_at: str
    layer_count: int
    geometry_count: int
