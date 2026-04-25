export interface Bounds {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
}

export interface LayerInfo {
  layer: number | string;
  datatype: number;
  name: string;
  polygon_count: number;
}

export interface Geometry {
  id: string;
  type: string;
  layer: number | string;
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

export interface DevicePort {
  id: string;
  position: [number, number];
  layer: string;
}

export interface Device {
  id: string;
  type: "inductor" | "capacitor" | "resistor" | "pad" | "via_gnd";
  value: number;
  unit: string;
  turns?: number;
  layers: string[];
  bbox: [number, number, number, number];
  polygon_ids: string[];
  ports: DevicePort[];
  metrics: Record<string, number>;
}

export interface PolygonChange {
  polygon_id: string;
  old_points: number[][];
  new_points: number[][];
}

export interface Modification {
  id: string;
  device_id: string;
  device_type: string;
  old_value: number;
  new_value: number;
  changes: PolygonChange[];
}

export interface DiffChange {
  polygon_id: string;
  old_bbox: [number, number, number, number];
  new_bbox: [number, number, number, number];
  old_area: number;
  new_area: number;
}

export interface DrcRule {
  id?: string;
  type: "min_width" | "min_spacing" | "min_area" | "min_overlap" | "max_width";
  layer: string;
  layer2?: string;
  value: number;
  description: string;
}

export interface DrcViolation {
  rule_id: string;
  rule_type: string;
  description: string;
  severity: "error" | "warning";
  polygon_id: string;
  actual_value: number;
  required_value: number;
  location: [number, number];
}

export interface DrcResults {
  violations: DrcViolation[];
  summary: { total: number; errors: number; warnings: number };
  passed: boolean;
}

export interface SpiceDevice {
  instance_name: string;
  device_type: 'inductor' | 'capacitor' | 'resistor';
  value: number;
  unit: string;
  nets: string[];
  subcircuit: string;
}

export interface SpiceNetlist {
  devices: SpiceDevice[];
  subcircuits: Record<string, SpiceDevice[]>;
  global_nets: string[];
}

export interface MatchResult {
  spice_name: string;
  layout_id: string;
  spice_value: number;
  layout_value: number;
  confidence: number;
  match_method: string;
}

export interface MatchResponse {
  matches: MatchResult[];
  unmatched_spice: string[];
  unmatched_layout: string[];
}
