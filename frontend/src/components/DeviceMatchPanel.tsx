import { useState } from "react";
import { Button, Tag, Typography, Collapse, Empty, Space, Badge, Tooltip } from "antd";
import { SwapOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";
import type { MatchResult } from "../types";

const { Text } = Typography;

interface MatchResultWithStatus extends MatchResult {
  status: "high" | "medium" | "low";
}

function getConfidenceStatus(confidence: number): "high" | "medium" | "low" {
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.5) return "medium";
  return "low";
}

function getConfidenceColor(status: "high" | "medium" | "low"): string {
  switch (status) {
    case "high": return "green";
    case "medium": return "gold";
    case "low": return "red";
  }
}

function getConfidenceIcon(status: "high" | "medium" | "low") {
  switch (status) {
    case "high": return <CheckCircleOutlined />;
    case "medium": return <WarningOutlined />;
    case "low": return <CloseCircleOutlined />;
  }
}

function formatValue(value: number, unit: string): string {
  if (value === 0) return `0 ${unit}`;
  const abs = Math.abs(value);
  if (abs >= 1e-3 && abs < 1) return `${(value * 1e3).toFixed(3)} m${unit}`;
  if (abs >= 1e-6 && abs < 1e-3) return `${(value * 1e6).toFixed(3)} μ${unit}`;
  if (abs >= 1e-9 && abs < 1e-6) return `${(value * 1e9).toFixed(3)} n${unit}`;
  if (abs >= 1e-12 && abs < 1e-9) return `${(value * 1e12).toFixed(3)} p${unit}`;
  return `${value} ${unit}`;
}

interface MatchItemProps {
  match: MatchResultWithStatus;
}

function MatchItem({ match }: MatchItemProps) {
  const status = match.status;
  const color = getConfidenceColor(status);
  const icon = getConfidenceIcon(status);

  return (
    <div
      style={{
        padding: "8px 10px",
        marginBottom: 6,
        borderRadius: 4,
        background: "#fafafa",
        border: `1px solid ${status === "high" ? "#d9d9d9" : status === "medium" ? "#ffe58f" : "#ffccc7"}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <Tag color={color} icon={icon} style={{ margin: 0 }}>
          {(match.confidence * 100).toFixed(0)}%
        </Tag>
        <Text strong style={{ fontSize: 12 }}>{match.spice_name}</Text>
        <Text type="secondary" style={{ fontSize: 11 }}>→</Text>
        <Text code style={{ fontSize: 11 }}>{match.layout_id}</Text>
        <Tag color="blue" style={{ marginLeft: "auto", fontSize: 10 }}>
          {match.match_method}
        </Tag>
      </div>
      <div style={{ display: "flex", gap: 12, fontSize: 11 }}>
        <Text type="secondary">
          SPICE: <Text style={{ fontFamily: "monospace" }}>{formatValue(match.spice_value, "H")}</Text>
        </Text>
        <Text type="secondary">
          Layout: <Text style={{ fontFamily: "monospace" }}>{formatValue(match.layout_value, "H")}</Text>
        </Text>
      </div>
    </div>
  );
}

interface UnmatchedItemProps {
  id: string;
  type: "spice" | "layout";
}

function UnmatchedItem({ id, type }: UnmatchedItemProps) {
  return (
    <div
      style={{
        padding: "4px 8px",
        marginBottom: 4,
        borderRadius: 4,
        background: type === "spice" ? "#fff2f0" : "#fffbe6",
        border: `1px solid ${type === "spice" ? "#ffccc7" : "#ffe58f"}`,
        fontSize: 12,
        fontFamily: "monospace",
      }}
    >
      <Text type="secondary" style={{ fontSize: 10 }}>
        {type === "spice" ? "SPICE" : "Layout"}
      </Text>{" "}
      <Text>{id}</Text>
    </div>
  );
}

export default function DeviceMatchPanel() {
  const { currentProject, matchDevices, loading } = useProjectStore();
  const [matchResults, setMatchResults] = useState<MatchResult[] | null>(null);
  const [matching, setMatching] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  const handleMatch = async () => {
    if (!currentProject) return;
    setMatching(true);
    setMatchError(null);
    try {
      const result = await matchDevices(currentProject.id);
      setMatchResults(result.matches ?? []);
    } catch (e: unknown) {
      setMatchError(e instanceof Error ? e.message : "Match failed");
    }
    setMatching(false);
  };

  const matchedWithStatus: MatchResultWithStatus[] = (matchResults ?? []).map((m) => ({
    ...m,
    status: getConfidenceStatus(m.confidence),
  }));

  const highConfidence = matchedWithStatus.filter((m) => m.status === "high");
  const mediumConfidence = matchedWithStatus.filter((m) => m.status === "medium");
  const lowConfidence = matchedWithStatus.filter((m) => m.status === "low");

  const unmatchedSpice = matchResults?.length
    ? (matchResults.length > 0 ? [] : [])
    : [];

  const collapseItems = [
    highConfidence.length > 0 && {
      key: "high",
      label: (
        <span>
          <Badge status="success" />
          <CheckCircleOutlined style={{ marginRight: 6 }} />
          高置信度匹配
          <Tag color="green" style={{ marginLeft: 8 }}>{highConfidence.length}</Tag>
        </span>
      ),
      children: (
        <div>
          {highConfidence.map((m) => (
            <MatchItem key={`${m.spice_name}-${m.layout_id}`} match={m} />
          ))}
        </div>
      ),
    },
    mediumConfidence.length > 0 && {
      key: "medium",
      label: (
        <span>
          <Badge status="warning" />
          <WarningOutlined style={{ marginRight: 6 }} />
          中置信度匹配
          <Tag color="gold" style={{ marginLeft: 8 }}>{mediumConfidence.length}</Tag>
        </span>
      ),
      children: (
        <div>
          {mediumConfidence.map((m) => (
            <MatchItem key={`${m.spice_name}-${m.layout_id}`} match={m} />
          ))}
        </div>
      ),
    },
    lowConfidence.length > 0 && {
      key: "low",
      label: (
        <span>
          <Badge status="error" />
          <CloseCircleOutlined style={{ marginRight: 6 }} />
          低置信度匹配
          <Tag color="red" style={{ marginLeft: 8 }}>{lowConfidence.length}</Tag>
        </span>
      ),
      children: (
        <div>
          {lowConfidence.map((m) => (
            <MatchItem key={`${m.spice_name}-${m.layout_id}`} match={m} />
          ))}
        </div>
      ),
    },
  ].filter(Boolean) as Collapse["items"];

  const totalMatched = matchedWithStatus.length;
  const totalUnmatched = (matchResults?.length ?? 0) > 0
    ? (matchResults?.[0] ? (matchResults?.length ?? 0) : 0)
    : 0;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: 12 }}>
      <Text strong style={{ fontSize: 14, marginBottom: 8, display: "block" }}>
        网表匹配
      </Text>

      {!currentProject && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          请先选择项目
        </Text>
      )}

      {currentProject && (
        <Button
          type="primary"
          icon={<SwapOutlined />}
          loading={matching || loading}
          onClick={handleMatch}
          style={{ marginBottom: 12 }}
        >
          执行匹配
        </Button>
      )}

      {matchError && (
        <Text type="danger" style={{ fontSize: 12, marginBottom: 8 }}>
          {matchError}
        </Text>
      )}

      {matchResults === null && !matching && (
        <Empty
          description="点击「执行匹配」开始网表匹配"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {matchResults !== null && matchResults.length === 0 && (
        <Empty
          description="未找到任何匹配结果"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {totalMatched > 0 && (
        <div style={{ flex: 1, overflowY: "auto" }}>
          <div style={{ marginBottom: 12 }}>
            <Space size="small" wrap>
              <Tag color="green">高置信 {highConfidence.length}</Tag>
              <Tag color="gold">中置信 {mediumConfidence.length}</Tag>
              <Tag color="red">低置信 {lowConfidence.length}</Tag>
            </Space>
          </div>

          <Collapse
            items={collapseItems}
            defaultActiveKey={["high", "medium", "low"]}
            size="small"
            style={{ background: "transparent" }}
          />
        </div>
      )}
    </div>
  );
}
