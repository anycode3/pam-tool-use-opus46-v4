import { useState } from "react";
import { Button, Checkbox, Tag, Typography, Space, Divider } from "antd";
import { useProjectStore } from "../store/useProjectStore";
import LayerMappingDialog from "./LayerMappingDialog";

const { Text } = Typography;

export default function LayerPanel() {
  const {
    layoutData,
    layerMapping,
    visibleLayers,
    toggleLayerVisibility,
    setAllLayersVisible,
    setAllLayersHidden,
  } = useProjectStore();
  const [mappingOpen, setMappingOpen] = useState(false);

  if (!layoutData || layoutData.layers.length === 0) return null;

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <Text strong>图层</Text>
        <Button
          size="small"
          type="link"
          onClick={() => setMappingOpen(true)}
          style={{ padding: 0, fontSize: 12 }}
        >
          配置映射
        </Button>
      </div>

      <Space style={{ marginBottom: 8 }}>
        <Button size="small" onClick={setAllLayersVisible}>全部显示</Button>
        <Button size="small" onClick={setAllLayersHidden}>全部隐藏</Button>
      </Space>

      <Divider style={{ margin: "8px 0" }} />

      <div style={{ maxHeight: 300, overflowY: "auto" }}>
        {layoutData.layers.map((layer) => {
          const mappedName = layerMapping[layer.name];
          return (
            <div
              key={layer.name}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "3px 0",
              }}
            >
              <Checkbox
                checked={!!visibleLayers[layer.name]}
                onChange={() => toggleLayerVisibility(layer.name)}
              />
              <Text style={{ fontSize: 12, minWidth: 32 }}>{layer.name}</Text>
              {mappedName && (
                <Tag color="blue" style={{ fontSize: 11, padding: "0 4px", lineHeight: "18px" }}>
                  {mappedName}
                </Tag>
              )}
              <Text type="secondary" style={{ fontSize: 11, marginLeft: "auto" }}>
                {layer.polygon_count}
              </Text>
            </div>
          );
        })}
      </div>

      <LayerMappingDialog open={mappingOpen} onClose={() => setMappingOpen(false)} />
    </div>
  );
}
