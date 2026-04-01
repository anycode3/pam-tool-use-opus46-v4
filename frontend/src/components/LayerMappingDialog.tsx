import { useState, useEffect } from "react";
import { Modal, Select, Space, Typography } from "antd";
import { useProjectStore } from "../store/useProjectStore";

const { Text } = Typography;

const STANDARD_LAYERS = ["ME1", "ME2", "TFR", "VA1", "GND"];

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function LayerMappingDialog({ open, onClose }: Props) {
  const { layoutData, layerMapping, currentProject, saveLayerMapping } = useProjectStore();
  const [localMappings, setLocalMappings] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setLocalMappings({ ...layerMapping });
    }
  }, [open, layerMapping]);

  const handleSave = async () => {
    if (!currentProject) return;
    setSaving(true);
    await saveLayerMapping(currentProject.id, localMappings);
    setSaving(false);
    onClose();
  };

  const handleChange = (layerName: string, value: string | undefined) => {
    setLocalMappings((prev) => {
      const next = { ...prev };
      if (value) {
        next[layerName] = value;
      } else {
        delete next[layerName];
      }
      return next;
    });
  };

  const layers = layoutData?.layers ?? [];

  return (
    <Modal
      title="图层映射配置"
      open={open}
      onOk={handleSave}
      onCancel={onClose}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      width={480}
    >
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          将源图层映射到标准图层名称
        </Text>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {layers.map((layer) => (
          <Space key={layer.name} style={{ width: "100%", justifyContent: "space-between" }}>
            <Text style={{ minWidth: 80, fontFamily: "monospace" }}>{layer.name}</Text>
            <Select
              style={{ width: 160 }}
              placeholder="(无)"
              allowClear
              value={localMappings[layer.name] ?? undefined}
              onChange={(val) => handleChange(layer.name, val)}
              options={[
                ...STANDARD_LAYERS.map((name) => ({ label: name, value: name })),
              ]}
            />
          </Space>
        ))}
        {layers.length === 0 && (
          <Text type="secondary">无可用图层</Text>
        )}
      </div>
    </Modal>
  );
}
