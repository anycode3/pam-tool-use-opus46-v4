import { Typography } from "antd";
import type { PolygonChange } from "../types";

const { Text } = Typography;

interface PolygonDiffPreviewProps {
  changes: PolygonChange[];
}

export default function PolygonDiffPreview({ changes }: PolygonDiffPreviewProps) {
  if (!changes || changes.length === 0) return null;

  // Compute unified bounding box from all old and new points
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

  for (const change of changes) {
    for (const pts of [change.old_points, change.new_points]) {
      for (const [x, y] of pts) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }

  // Add 5% padding
  const dx = maxX - minX;
  const dy = maxY - minY;
  const pad = Math.max(dx, dy) * 0.05;
  minX -= pad;
  minY -= pad;
  maxX += pad;
  maxY += pad;

  const width = maxX - minX;
  const height = maxY - minY;

  // SVG viewBox (Y-axis flipped for layout coordinates)
  const viewBox = `${minX} ${-maxY} ${width} ${height}`;

  return (
    <div style={{ marginTop: 8 }}>
      <Text style={{ fontSize: 11, display: "block", marginBottom: 4 }}>几何对比</Text>
      <svg
        width="100%"
        height={160}
        viewBox={viewBox}
        style={{ border: "1px solid #d9d9d9", borderRadius: 4, background: "#fafafa" }}
      >
        <g transform="scale(1,-1)">
          {/* Old polygons in red */}
          {changes.map((change, i) => (
            <polygon
              key={`old-${i}`}
              points={change.old_points.map(([x, y]) => `${x},${y}`).join(" ")}
              fill="rgba(255,77,79,0.3)"
              stroke="#ff4d4f"
              strokeWidth={width * 0.002}
            />
          ))}
          {/* New polygons in green */}
          {changes.map((change, i) => (
            <polygon
              key={`new-${i}`}
              points={change.new_points.map(([x, y]) => `${x},${y}`).join(" ")}
              fill="rgba(82,196,26,0.3)"
              stroke="#52c41a"
              strokeWidth={width * 0.002}
            />
          ))}
        </g>
      </svg>
      <div style={{ display: "flex", gap: 12, marginTop: 4, fontSize: 10 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 12, height: 12, background: "rgba(255,77,79,0.5)", border: "1px solid #ff4d4f" }} />
          <Text type="secondary" style={{ fontSize: 10 }}>修改前</Text>
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 12, height: 12, background: "rgba(82,196,26,0.5)", border: "1px solid #52c41a" }} />
          <Text type="secondary" style={{ fontSize: 10 }}>修改后</Text>
        </span>
      </div>
    </div>
  );
}
