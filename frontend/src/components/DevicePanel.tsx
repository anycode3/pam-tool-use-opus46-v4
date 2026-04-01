import { useState } from "react";
import type { ReactNode } from "react";
import {
  Button,
  Collapse,
  Tag,
  Typography,
  Divider,
  Alert,
  Descriptions,
  Empty,
} from "antd";
import {
  ThunderboltOutlined,
  ApiOutlined,
  MinusCircleOutlined,
  PushpinOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";
import type { Device } from "../types";

const { Text } = Typography;

const DEVICE_TYPE_LABELS: Record<Device["type"], string> = {
  inductor: "电感",
  capacitor: "电容",
  resistor: "电阻",
  pad: "焊盘",
  via_gnd: "地孔",
};

const DEVICE_TYPE_COLORS: Record<Device["type"], string> = {
  inductor: "blue",
  capacitor: "green",
  resistor: "orange",
  pad: "purple",
  via_gnd: "red",
};

const DEVICE_TYPE_ICONS: Record<Device["type"], ReactNode> = {
  inductor: <ThunderboltOutlined />,
  capacitor: <ApiOutlined />,
  resistor: <MinusCircleOutlined />,
  pad: <PushpinOutlined />,
  via_gnd: <ApartmentOutlined />,
};

const GROUP_ORDER: Device["type"][] = [
  "inductor",
  "capacitor",
  "resistor",
  "pad",
  "via_gnd",
];

function formatValue(value: number, unit: string): string {
  if (value === 0) return `0 ${unit}`;
  const abs = Math.abs(value);
  if (abs >= 1e-3 && abs < 1) return `${(value * 1e3).toFixed(3)} m${unit}`;
  if (abs >= 1e-6 && abs < 1e-3) return `${(value * 1e6).toFixed(3)} μ${unit}`;
  if (abs >= 1e-9 && abs < 1e-6) return `${(value * 1e9).toFixed(3)} n${unit}`;
  if (abs >= 1e-12 && abs < 1e-9) return `${(value * 1e12).toFixed(3)} p${unit}`;
  return `${value} ${unit}`;
}

interface DeviceItemProps {
  device: Device;
  isSelected: boolean;
  onClick: () => void;
}

function DeviceItem({ device, isSelected, onClick }: DeviceItemProps) {
  const label = DEVICE_TYPE_LABELS[device.type];
  const color = DEVICE_TYPE_COLORS[device.type];

  return (
    <div
      onClick={onClick}
      style={{
        padding: "6px 8px",
        cursor: "pointer",
        borderRadius: 4,
        background: isSelected ? "#e6f4ff" : "transparent",
        border: isSelected ? "1px solid #1890ff" : "1px solid transparent",
        marginBottom: 4,
        transition: "background 0.15s",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <Tag color={color} style={{ fontSize: 11, margin: 0 }}>
          {label}
        </Tag>
        <Text style={{ fontSize: 12, flex: 1 }}>
          {formatValue(device.value, device.unit)}
        </Text>
        <Text type="secondary" style={{ fontSize: 11 }}>
          {device.polygon_ids.length} poly
        </Text>
      </div>

      {isSelected && (
        <div style={{ marginTop: 8 }}>
          <Divider style={{ margin: "6px 0" }} />
          <Descriptions size="small" column={1} labelStyle={{ fontSize: 11 }} contentStyle={{ fontSize: 11 }}>
            <Descriptions.Item label="ID">
              <Text copyable style={{ fontSize: 11 }}>{device.id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="图层">
              {device.layers.join(", ") || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="多边形数">
              {device.polygon_ids.length}
            </Descriptions.Item>
            <Descriptions.Item label="端口数">
              {device.ports.length}
            </Descriptions.Item>
            {device.turns !== undefined && (
              <Descriptions.Item label="匝数">
                {device.turns}
              </Descriptions.Item>
            )}
            {Object.entries(device.metrics).map(([k, v]) => (
              <Descriptions.Item key={k} label={k}>
                {typeof v === "number" ? v.toFixed(4) : String(v)}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </div>
      )}
    </div>
  );
}

export default function DevicePanel() {
  const {
    currentProject,
    layerMapping,
    devices,
    selectedDevice,
    recognizeDevices,
    selectDevice,
    loading,
  } = useProjectStore();

  const [recognizing, setRecognizing] = useState(false);

  const hasMappings = Object.keys(layerMapping).length > 0;

  const handleRecognize = async () => {
    if (!currentProject) return;
    setRecognizing(true);
    await recognizeDevices(currentProject.id);
    setRecognizing(false);
  };

  const grouped = GROUP_ORDER.reduce<Record<Device["type"], Device[]>>(
    (acc, type) => {
      acc[type] = devices.filter((d) => d.type === type);
      return acc;
    },
    { inductor: [], capacitor: [], resistor: [], pad: [], via_gnd: [] }
  );

  const collapseItems = GROUP_ORDER.filter((type) => grouped[type].length > 0).map(
    (type) => ({
      key: type,
      label: (
        <span>
          <span style={{ marginRight: 6 }}>{DEVICE_TYPE_ICONS[type]}</span>
          {DEVICE_TYPE_LABELS[type]}
          <Tag
            color={DEVICE_TYPE_COLORS[type]}
            style={{ marginLeft: 8, fontSize: 11 }}
          >
            {grouped[type].length}
          </Tag>
        </span>
      ),
      children: (
        <div>
          {grouped[type].map((device) => (
            <DeviceItem
              key={device.id}
              device={device}
              isSelected={selectedDevice?.id === device.id}
              onClick={() =>
                selectDevice(selectedDevice?.id === device.id ? null : device)
              }
            />
          ))}
        </div>
      ),
    })
  );

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: 12 }}>
      <Text strong style={{ fontSize: 14, marginBottom: 8, display: "block" }}>
        器件识别
      </Text>

      {!currentProject && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          请先选择项目
        </Text>
      )}

      {currentProject && !hasMappings && (
        <Alert
          type="warning"
          message="请先配置图层映射"
          description="在左侧图层面板点击「配置映射」设置后再识别器件。"
          showIcon
          style={{ fontSize: 12, marginBottom: 8 }}
        />
      )}

      {currentProject && (
        <Button
          type="primary"
          loading={recognizing || loading}
          onClick={handleRecognize}
          disabled={!hasMappings}
          style={{ marginBottom: 12 }}
        >
          识别器件
        </Button>
      )}

      {devices.length === 0 && currentProject ? (
        <Empty description="暂无器件数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div style={{ flex: 1, overflowY: "auto" }}>
          <Collapse
            items={collapseItems}
            defaultActiveKey={GROUP_ORDER}
            size="small"
            style={{ background: "transparent" }}
          />
        </div>
      )}
    </div>
  );
}
