import { useState, useRef } from "react";
import {
  Button,
  Form,
  Select,
  InputNumber,
  Input,
  Typography,
  Space,
  Tag,
  Empty,
  Divider,
  Tooltip,
  message,
} from "antd";
import { PlusOutlined, DeleteOutlined, UploadOutlined, SaveOutlined, PlayCircleOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";
import type { DrcRule } from "../types";

const { Text } = Typography;

const RULE_TYPE_LABELS: Record<DrcRule["type"], string> = {
  min_width: "最小线宽",
  min_spacing: "最小间距",
  min_area: "最小面积",
  min_overlap: "最小重叠",
  max_width: "最大线宽",
};

const RULE_TYPE_COLORS: Record<DrcRule["type"], string> = {
  min_width: "blue",
  min_spacing: "green",
  min_area: "purple",
  min_overlap: "orange",
  max_width: "red",
};

const SPACING_OVERLAP_TYPES: DrcRule["type"][] = ["min_spacing", "min_overlap"];

export default function DrcRulesPanel() {
  const {
    currentProject,
    layerMapping,
    drcRules,
    saveDrcRules,
    runDrc,
    loading,
  } = useProjectStore();

  const [localRules, setLocalRules] = useState<DrcRule[]>(drcRules);
  const [form] = Form.useForm();
  const [selectedType, setSelectedType] = useState<DrcRule["type"]>("min_width");
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync local rules when store rules change (e.g., after fetch)
  // We use a separate local state to allow unsaved edits
  const availableLayers = Object.keys(layerMapping).length > 0
    ? Object.keys(layerMapping)
    : [];

  const needsLayer2 = SPACING_OVERLAP_TYPES.includes(selectedType);

  const handleAddRule = () => {
    form.validateFields().then((values) => {
      const newRule: DrcRule = {
        type: values.type,
        layer: values.layer,
        layer2: needsLayer2 ? values.layer2 : undefined,
        value: values.value,
        description: values.description || "",
      };
      setLocalRules((prev) => [...prev, newRule]);
      form.resetFields(["layer", "layer2", "value", "description"]);
    });
  };

  const handleDeleteRule = (index: number) => {
    setLocalRules((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!currentProject) return;
    setSaving(true);
    await saveDrcRules(localRules);
    setSaving(false);
    message.success("规则已保存");
  };

  const handleRun = async () => {
    if (!currentProject) return;
    // Save first, then run
    setRunning(true);
    await saveDrcRules(localRules);
    await runDrc();
    setRunning(false);
    message.success("DRC 运行完成");
  };

  const handleUploadFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        const rules: DrcRule[] = Array.isArray(parsed) ? parsed : parsed.rules ?? [];
        setLocalRules(rules);
        message.success(`已加载 ${rules.length} 条规则`);
      } catch {
        message.error("JSON 文件解析失败");
      }
    };
    reader.readAsText(file);
    // Reset file input so same file can be re-uploaded
    e.target.value = "";
  };

  if (!currentProject) {
    return (
      <div style={{ padding: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>请先选择项目</Text>
      </div>
    );
  }

  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 12 }}>
      <Text strong style={{ fontSize: 14 }}>DRC 规则配置</Text>

      {/* Add rule form */}
      <div style={{ background: "#fafafa", borderRadius: 6, padding: 10, border: "1px solid #f0f0f0" }}>
        <Text strong style={{ fontSize: 12, display: "block", marginBottom: 8 }}>添加规则</Text>
        <Form form={form} layout="vertical" size="small" initialValues={{ type: "min_width" }}>
          <Form.Item name="type" label="规则类型" rules={[{ required: true }]} style={{ marginBottom: 8 }}>
            <Select
              options={Object.entries(RULE_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
              onChange={(v) => setSelectedType(v as DrcRule["type"])}
            />
          </Form.Item>

          <Form.Item name="layer" label="目标层" rules={[{ required: true, message: "请选择图层" }]} style={{ marginBottom: 8 }}>
            <Select
              showSearch
              placeholder="选择图层"
              options={availableLayers.map((l) => ({ value: l, label: l }))}
              notFoundContent={availableLayers.length === 0 ? "请先配置图层映射" : "无匹配图层"}
            />
          </Form.Item>

          {needsLayer2 && (
            <Form.Item name="layer2" label="目标层 2" rules={[{ required: true, message: "请选择第二图层" }]} style={{ marginBottom: 8 }}>
              <Select
                showSearch
                placeholder="选择第二图层"
                options={availableLayers.map((l) => ({ value: l, label: l }))}
                notFoundContent={availableLayers.length === 0 ? "请先配置图层映射" : "无匹配图层"}
              />
            </Form.Item>
          )}

          <Form.Item name="value" label="值 (µm)" rules={[{ required: true, message: "请输入数值" }]} style={{ marginBottom: 8 }}>
            <InputNumber min={0} step={0.01} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="description" label="描述" style={{ marginBottom: 8 }}>
            <Input placeholder="可选描述" />
          </Form.Item>

          <Button
            type="dashed"
            icon={<PlusOutlined />}
            onClick={handleAddRule}
            style={{ width: "100%" }}
            size="small"
          >
            添加规则
          </Button>
        </Form>
      </div>

      {/* Rules list */}
      <div>
        <Text strong style={{ fontSize: 12, display: "block", marginBottom: 6 }}>
          规则列表 ({localRules.length})
        </Text>
        {localRules.length === 0 ? (
          <Empty description="暂无规则" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {localRules.map((rule, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "4px 8px",
                  background: "#fff",
                  border: "1px solid #f0f0f0",
                  borderRadius: 4,
                }}
              >
                <Tag color={RULE_TYPE_COLORS[rule.type]} style={{ fontSize: 11, margin: 0, flexShrink: 0 }}>
                  {RULE_TYPE_LABELS[rule.type]}
                </Tag>
                <Text style={{ fontSize: 11, flex: 1, minWidth: 0 }} ellipsis>
                  {rule.layer}{rule.layer2 ? `↔${rule.layer2}` : ""}: {rule.value}µm
                  {rule.description ? ` (${rule.description})` : ""}
                </Text>
                <Tooltip title="删除">
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleDeleteRule(idx)}
                    style={{ flexShrink: 0 }}
                  />
                </Tooltip>
              </div>
            ))}
          </div>
        )}
      </div>

      <Divider style={{ margin: "4px 0" }} />

      {/* Action buttons */}
      <Space direction="vertical" style={{ width: "100%" }}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        <Button
          icon={<UploadOutlined />}
          onClick={handleUploadFile}
          style={{ width: "100%" }}
          size="small"
        >
          上传规则文件
        </Button>
        <Button
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saving || loading}
          style={{ width: "100%" }}
          size="small"
        >
          保存规则
        </Button>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleRun}
          loading={running || loading}
          disabled={localRules.length === 0}
          style={{ width: "100%" }}
          size="small"
        >
          运行DRC
        </Button>
      </Space>
    </div>
  );
}
