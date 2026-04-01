export interface Bounds {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
}

export interface LayerInfo {
  layer: number;
  datatype: number;
  name: string;
  polygon_count: number;
}

export interface Geometry {
  id: string;
  type: string;
  layer: number;
  datatype: number;
  points: number[][];
  properties: Record<string, unknown>;
}

export interface LayoutData {
  bounds: Bounds;
  layers: LayerInfo[];
  geometries: Geometry[];
}

export interface ProjectInfo {
  id: string;
  name: string;
  file_type: string;
  file_size: number;
  created_at: string;
  layer_count?: number;
  geometry_count?: number;
}
