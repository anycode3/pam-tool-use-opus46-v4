import { useState } from "react";
import {
  Button,
  InputNumber,
  Radio,
  Space,
  Typography,
  Descriptions,
  Alert,
} from "antd";
import { useProjectStore } from "../store/useProjectStore";
import type { Device, Modification } from "../types";

const { Text } = Typography;

interface DeviceModifyPanelProps {
  device: Device;
}

export default function DeviceModifyPanel({ device }: DeviceModifyPanelProps) {
  const { modifyDevice, modifications, loading } = useProjectStore();

  const [newValue, setNewValue] = useState<number>(device.value);
  const [mode, setMode] = useState<"auto" | "manual">("auto");
  const [manualWidth, setManualWidth] = useState<number>(1.0);
  const [manualLength, setManualLength] = useState<number>(1.0);
  const [previewing, setPreviewing] = useState(false);

  const latestMod = modifications.filter((m) => m.device_id === device.id).at(-1);

  const handlePreview = async () => {
    setPreviewing(true);
    const manualParams = mode === "manual" ? { width: manualWidth, length: manualLength } : undefined;
    await modifyDevice(device.id, newValue, mode, manualParams);
    setPreviewing(false);
  };

  return (
    <Space direction="vertical" style={{ width: "100%" }} size={12}>
      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          当前值: {device.value} {device.unit}
        </Text>
      </div>

      <div>
        <Text style={{ fontSize: 12, display: "block", marginBottom: 4 }}>新值 ({device.unit})</Text>
        <InputNumber
          style={{ width: "100%" }}
          value={newValue}
          onChange={(v) => setNewValue(v ?? device.value)}
          step={0.1}
          size="small"
        />
      </div>

      <div>
        <Text style={{ fontSize: 12, display: "block", marginBottom: 4 }}>模式</Text>
        <Radio.Group
          size="small"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <Radio.Button value="auto">自动</Radio.Button>
          <Radio.Button value="manual">手动</Radio.Button>
        </Radio.Group>
      </div>

      {mode === "manual" && (
        <>
          <div>
            <Text style={{ fontSize: 12, display: "block", marginBottom: 4 }}>宽度 (μm)</Text>
            <InputNumber
              style={{ width: "100%" }}
              value={manualWidth}
              onChange={(v) => setManualWidth(v ?? 1.0)}
              step={0.1}
              min={0.01}
              size="small"
            />
          </div>
          <div>
            <Text style={{ fontSize: 12, display: "block", marginBottom: 4 }}>长度 (μm)</Text>
            <InputNumber
              style={{ width: "100%" }}
              value={manualLength}
              onChange={(v) => setManualLength(v ?? 1.0)}
              step={0.1}
              min={0.01}
              size="small"
            />
          </div>
        </>
      )}

      <Button
        type="primary"
        size="small"
        style={{ width: "100%" }}
        loading={previewing || loading}
        onClick={handlePreview}
      >
        预览修改
      </Button>

      {latestMod && (
        <Alert
          type="success"
          showIcon
          message={`${latestMod.old_value} → ${latestMod.new_value} ${device.unit}，${latestMod.changes.length} 个多边形变更`}
          description="已在版图中高亮显示修改对比（红=修改前，绿=修改后）"
          style={{ fontSize: 12 }}
        />
      )}
    </Space>
  );
}
