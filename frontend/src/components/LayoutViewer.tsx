import { useMemo, useState, useCallback } from "react";
import { DeckGL, OrthographicView } from "deck.gl";
import { SolidPolygonLayer, ScatterplotLayer } from "deck.gl";
import { useProjectStore } from "../store/useProjectStore";
import type { Geometry, DrcViolation } from "../types";

const LAYER_COLORS: Record<number, [number, number, number, number]> = {
  0: [65, 105, 225, 160],
  1: [220, 20, 60, 160],
  2: [50, 205, 50, 160],
  3: [255, 165, 0, 160],
  4: [148, 103, 189, 160],
  5: [255, 215, 0, 160],
  6: [0, 206, 209, 160],
  7: [255, 99, 71, 160],
};

const HIGHLIGHT_COLOR: [number, number, number, number] = [255, 255, 0, 220];
const DEVICE_HIGHLIGHT_COLOR: [number, number, number, number] = [0, 255, 255, 230];

function getLayerColor(layer: number): [number, number, number, number] {
  return (
    LAYER_COLORS[layer % Object.keys(LAYER_COLORS).length] ?? [
      128, 128, 128, 160,
    ]
  );
}

export default function LayoutViewer() {
  const { layoutData, visibleLayers, selectedDevice, drcResults, highlightedViolationPolygonId } = useProjectStore();
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const highlightedPolygonIds = useMemo<Set<string>>(() => {
    if (!selectedDevice) return new Set();
    return new Set(selectedDevice.polygon_ids);
  }, [selectedDevice]);

  const violationPolygonIds = useMemo<Set<string>>(() => {
    if (!drcResults) return new Set();
    return new Set(drcResults.violations.map((v) => v.polygon_id));
  }, [drcResults]);

  const initialViewState = useMemo(() => {
    if (!layoutData) return { target: [0, 0, 0] as [number, number, number], zoom: 0 };
    const { bounds } = layoutData;
    const cx = (bounds.min_x + bounds.max_x) / 2;
    const cy = (bounds.min_y + bounds.max_y) / 2;
    const dx = bounds.max_x - bounds.min_x;
    const dy = bounds.max_y - bounds.min_y;
    const span = Math.max(dx, dy, 1);
    const zoom = Math.log2(800 / span);
    return { target: [cx, cy, 0] as [number, number, number], zoom };
  }, [layoutData]);

  const onHover = useCallback((info: { object?: Geometry | null }) => {
    setHoveredId(info.object?.id ?? null);
  }, []);

  const onClick = useCallback((info: { object?: Geometry | null }) => {
    setSelectedId(info.object?.id ?? null);
  }, []);

  const layers = useMemo(() => {
    if (!layoutData || layoutData.geometries.length === 0) return [];

    const visibleGeometries = layoutData.geometries.filter((g) => {
      const layerName = `${g.layer}/${g.datatype}`;
      // If visibleLayers has an entry, respect it; otherwise show by default
      return layerName in visibleLayers ? visibleLayers[layerName] : true;
    });

    const polygonLayer = new SolidPolygonLayer<Geometry>({
      id: "layout-polygons",
      data: visibleGeometries,
      getPolygon: (d: Geometry) => d.points as [number, number][],
      getFillColor: (d: Geometry) => {
        if (highlightedViolationPolygonId === d.id) return [255, 80, 0, 230];
        if (violationPolygonIds.has(d.id)) return [255, 100, 50, 180];
        if (highlightedPolygonIds.has(d.id)) return DEVICE_HIGHLIGHT_COLOR;
        if (d.id === selectedId || d.id === hoveredId) return HIGHLIGHT_COLOR;
        return getLayerColor(d.layer);
      },
      pickable: true,
      updateTriggers: {
        getFillColor: [hoveredId, selectedId, highlightedPolygonIds, violationPolygonIds, highlightedViolationPolygonId],
      },
    });

    const result: (typeof polygonLayer | ScatterplotLayer<DrcViolation>)[] = [polygonLayer];

    // Add violation markers when DRC results exist
    if (drcResults && drcResults.violations.length > 0) {
      result.push(
        new ScatterplotLayer<DrcViolation>({
          id: "drc-violation-markers",
          data: drcResults.violations,
          getPosition: (d: DrcViolation) => [d.location[0], d.location[1], 0],
          getRadius: 0.5,
          radiusMinPixels: 5,
          radiusMaxPixels: 14,
          getFillColor: (d: DrcViolation) =>
            d.severity === "error" ? [255, 50, 50, 220] : [255, 165, 0, 220],
          pickable: false,
          updateTriggers: {
            getFillColor: [],
          },
        })
      );
    }

    return result;
  }, [layoutData, visibleLayers, hoveredId, selectedId, highlightedPolygonIds, violationPolygonIds, drcResults, highlightedViolationPolygonId]);

  if (!layoutData) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#999",
          fontSize: 16,
        }}
      >
        请上传版图文件
      </div>
    );
  }

  return (
    <DeckGL
      views={new OrthographicView({ id: "ortho" })}
      initialViewState={initialViewState}
      controller={true}
      layers={layers}
      onHover={onHover}
      onClick={onClick}
      style={{ width: "100%", height: "100%" }}
      getCursor={({ isHovering }: { isHovering: boolean }) =>
        isHovering ? "pointer" : "grab"
      }
    />
  );
}
