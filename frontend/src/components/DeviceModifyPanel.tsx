import { useState } from "react";
import {
  Button,
  InputNumber,
  Radio,
  Space,
  Typography,
  Divider,
  Alert,
  Descriptions,
} from "antd";
import { DownloadOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";
import type { Device, Modification } from "../types";

const { Text } = Typography;

interface DeviceModifyPanelProps {
  device: Device;
}

export default function DeviceModifyPanel({ device }: DeviceModifyPanelProps) {
  const { modifyDevice, applyModifications, downloadLayout, modifications, loading } = useProjectStore();

  const [newValue, setNewValue] = useState<number>(device.value);
  const [mode, setMode] = useState<"auto" | "manual">("auto");
  const [manualWidth, setManualWidth] = useState<number>(1.0);
  const [manualLength, setManualLength] = useState<number>(1.0);
  const [preview, setPreview] = useState<Modification | null>(null);
  const [applied, setApplied] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Find latest modification for this device in the store
  const latestMod = modifications.filter((m) => m.device_id === device.id).at(-1);

  const handlePreview = async () => {
    setPreviewing(true);
    setApplied(false);
    setPreview(null);
    const manualParams = mode === "manual" ? { width: manualWidth, length: manualLength } : undefined;
    await modifyDevice(device.id, newValue, mode, manualParams);
    // After modifyDevice resolves, the modification is in store; read it from store
    setPreviewing(false);
  };

  const handleApply = async () => {
    setApplying(true);
    await applyModifications();
    setApplied(true);
    setApplying(false);
  };

  const handleDownload = async () => {
    setDownloading(true);
    await downloadLayout();
    setDownloading(false);
  };

  // Use store's latestMod as the preview result after previewing
  const mod = latestMod ?? preview;

  return (
    <div style={{ padding: "8px 0" }}>
      <Divider style={{ margin: "8px 0" }} />
      <Text strong style={{ fontSize: 13, display: "block", marginBottom: 8 }}>
        修改器件
      </Text>

      <Space direction="vertical" style={{ width: "100%" }} size={8}>
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

        {mod && (
          <div
            style={{
              background: "#f6ffed",
              border: "1px solid #b7eb8f",
              borderRadius: 4,
              padding: 8,
            }}
          >
            <Text strong style={{ fontSize: 12 }}>预览结果</Text>
            <Descriptions size="small" column={1} style={{ marginTop: 4 }} labelStyle={{ fontSize: 11 }} contentStyle={{ fontSize: 11 }}>
              <Descriptions.Item label="旧值">
                {mod.old_value} {device.unit}
              </Descriptions.Item>
              <Descriptions.Item label="新值">
                {mod.new_value} {device.unit}
              </Descriptions.Item>
              <Descriptions.Item label="变更多边形数">
                {mod.changes.length}
              </Descriptions.Item>
            </Descriptions>

            {applied ? (
              <Alert
                type="success"
                icon={<CheckCircleOutlined />}
                message="已应用修改"
                showIcon
                style={{ marginTop: 8, fontSize: 12 }}
              />
            ) : (
              <Button
                type="default"
                size="small"
                style={{ width: "100%", marginTop: 8 }}
                loading={applying}
                onClick={handleApply}
              >
                应用修改
              </Button>
            )}
          </div>
        )}

        {applied && (
          <Button
            type="primary"
            size="small"
            icon={<DownloadOutlined />}
            style={{ width: "100%" }}
            loading={downloading}
            onClick={handleDownload}
          >
            下载修改后版图
          </Button>
        )}
      </Space>
    </div>
  );
}
