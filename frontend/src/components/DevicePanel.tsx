import { useState, useEffect } from "react";
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
  Space,
  Popover,
} from "antd";
import {
  ThunderboltOutlined,
  ApiOutlined,
  MinusCircleOutlined,
  PushpinOutlined,
  ApartmentOutlined,
  DownloadOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  EditOutlined,
} from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";
import type { Device } from "../types";
import DeviceModifyPanel from "./DeviceModifyPanel";
import DiffViewer from "./DiffViewer";
import NetlistUploadDialog from "./NetlistUploadDialog";
import DeviceMatchPanel from "./DeviceMatchPanel";

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

const MODIFIABLE_TYPES: Set<Device["type"]> = new Set(["inductor", "capacitor", "resistor"]);

interface DeviceItemProps {
  device: Device;
  isSelected: boolean;
  onClick: () => void;
  onPopoverChange: (open: boolean) => void;
  popoverOpen: boolean;
}

function DeviceItem({ device, isSelected, onClick, onPopoverChange, popoverOpen }: DeviceItemProps) {
  const label = DEVICE_TYPE_LABELS[device.type];
  const color = DEVICE_TYPE_COLORS[device.type];

  const editButton = MODIFIABLE_TYPES.has(device.type) ? (
    <Popover
      placement="left"
      trigger="click"
      open={popoverOpen}
      onOpenChange={onPopoverChange}
      title={`修改 ${DEVICE_TYPE_LABELS[device.type]}`}
      content={<DeviceModifyPanel device={device} />}
      overlayStyle={{ width: 280 }}
      destroyTooltipOnHide
    >
      <Button
        size="small"
        type="link"
        icon={<EditOutlined />}
        style={{ fontSize: 11, padding: 0, height: "auto" }}
        onClick={(e) => e.stopPropagation()}
      />
    </Popover>
  ) : null;

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
        {editButton}
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
    modifications,
    applyModifications,
    downloadLayout,
    clearModifications,
    clearModificationPreview,
    loading,
  } = useProjectStore();

  const [recognizing, setRecognizing] = useState(false);
  const [applied, setApplied] = useState(false);
  const [applying, setApplying] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [popoverDeviceId, setPopoverDeviceId] = useState<string | null>(null);
  const [netlistDialogOpen, setNetlistDialogOpen] = useState(false);
  const [matchPanelOpen, setMatchPanelOpen] = useState(false);

  // Reset applied state when modifications change
  useEffect(() => {
    setApplied(false);
  }, [modifications.length]);

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

  const handlePopoverChange = (deviceId: string, open: boolean) => {
    if (open) {
      setPopoverDeviceId(deviceId);
      const device = devices.find((d) => d.id === deviceId);
      if (device) selectDevice(device);
    } else {
      setPopoverDeviceId(null);
      clearModificationPreview();
    }
  };

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
              popoverOpen={popoverDeviceId === device.id}
              onPopoverChange={(open) => handlePopoverChange(device.id, open)}
            />
          ))}
        </div>
      ),
    })
  );

  const handleApplyAll = async () => {
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

  const handleClear = () => {
    clearModifications();
    setApplied(false);
  };

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
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          <Button
            type="primary"
            loading={recognizing || loading}
            onClick={handleRecognize}
            disabled={!hasMappings}
          >
            识别器件
          </Button>
          <Button onClick={() => setNetlistDialogOpen(true)}>
            上传网表
          </Button>
          <Button onClick={() => setMatchPanelOpen(true)} disabled={devices.length === 0}>
            网表匹配
          </Button>
        </div>
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

          {modifications.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <Divider style={{ margin: "8px 0" }} />
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <Text strong style={{ fontSize: 13 }}>修改汇总</Text>
                <Tag color="blue">{modifications.length} 项</Tag>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
                {modifications.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      fontSize: 11,
                      padding: "4px 8px",
                      background: "#fafafa",
                      borderRadius: 4,
                      border: "1px solid #f0f0f0",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span>
                      <Tag
                        color={DEVICE_TYPE_COLORS[m.device_type as Device["type"]] ?? "default"}
                        style={{ fontSize: 10, margin: 0, marginRight: 6 }}
                      >
                        {DEVICE_TYPE_LABELS[m.device_type as Device["type"]] ?? m.device_type}
                      </Tag>
                      {m.old_value} → {m.new_value}
                    </span>
                    <Text type="secondary" style={{ fontSize: 10 }}>{m.changes.length} poly</Text>
                  </div>
                ))}
              </div>

              <Space style={{ width: "100%" }} direction="vertical" size={6}>
                {applied ? (
                  <>
                    <Alert
                      type="success"
                      icon={<CheckCircleOutlined />}
                      message="已应用全部修改"
                      showIcon
                      style={{ fontSize: 12 }}
                    />
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
                  </>
                ) : (
                  <Button
                    type="primary"
                    size="small"
                    style={{ width: "100%" }}
                    loading={applying}
                    onClick={handleApplyAll}
                  >
                    应用全部修改
                  </Button>
                )}
                <Button
                  size="small"
                  danger
                  ghost
                  icon={<DeleteOutlined />}
                  style={{ width: "100%" }}
                  onClick={handleClear}
                >
                  清除修改
                </Button>
              </Space>
            </div>
          )}

          <DiffViewer />
        </div>
      )}

      <NetlistUploadDialog
        open={netlistDialogOpen}
        onClose={() => setNetlistDialogOpen(false)}
        projectId={currentProject?.id || ''}
      />

      <DeviceMatchPanel
        open={matchPanelOpen}
        onClose={() => setMatchPanelOpen(false)}
        projectId={currentProject?.id || ''}
      />
    </div>
  );
}
