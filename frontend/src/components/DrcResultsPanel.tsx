import { Table, Tag, Typography, Badge, Empty, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";
import type { DrcViolation } from "../types";

const { Text } = Typography;

const SEVERITY_COLOR: Record<DrcViolation["severity"], string> = {
  error: "red",
  warning: "orange",
};

const SEVERITY_LABEL: Record<DrcViolation["severity"], string> = {
  error: "错误",
  warning: "警告",
};

export default function DrcResultsPanel() {
  const { drcResults, setHighlightedViolationPolygonId, highlightedViolationPolygonId } = useProjectStore();

  if (!drcResults) {
    return (
      <div style={{ padding: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>暂无 DRC 结果，请先运行 DRC。</Text>
      </div>
    );
  }

  const { violations, summary, passed } = drcResults;

  const columns: ColumnsType<DrcViolation> = [
    {
      title: "规则",
      dataIndex: "rule_type",
      key: "rule_type",
      width: 90,
      render: (type: string) => (
        <Text style={{ fontSize: 11 }}>{type}</Text>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      render: (desc: string) => (
        <Tooltip title={desc}>
          <Text style={{ fontSize: 11 }}>{desc}</Text>
        </Tooltip>
      ),
    },
    {
      title: "级别",
      dataIndex: "severity",
      key: "severity",
      width: 60,
      render: (sev: DrcViolation["severity"]) => (
        <Tag color={SEVERITY_COLOR[sev]} style={{ fontSize: 10, margin: 0 }}>
          {SEVERITY_LABEL[sev]}
        </Tag>
      ),
    },
    {
      title: "实际值",
      dataIndex: "actual_value",
      key: "actual_value",
      width: 70,
      render: (v: number) => <Text style={{ fontSize: 11 }}>{v.toFixed(3)}</Text>,
    },
    {
      title: "要求值",
      dataIndex: "required_value",
      key: "required_value",
      width: 70,
      render: (v: number) => <Text style={{ fontSize: 11 }}>{v.toFixed(3)}</Text>,
    },
  ];

  const handleRowClick = (record: DrcViolation) => {
    const newId = highlightedViolationPolygonId === record.polygon_id ? null : record.polygon_id;
    setHighlightedViolationPolygonId(newId);
  };

  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
      <Text strong style={{ fontSize: 14 }}>DRC 结果</Text>

      {/* Summary */}
      <div
        style={{
          background: passed ? "#f6ffed" : "#fff2f0",
          border: `1px solid ${passed ? "#b7eb8f" : "#ffccc7"}`,
          borderRadius: 6,
          padding: "8px 12px",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        {passed ? (
          <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 20 }} />
        ) : (
          <CloseCircleOutlined style={{ color: "#ff4d4f", fontSize: 20 }} />
        )}
        <div style={{ flex: 1 }}>
          <Text strong style={{ fontSize: 13, color: passed ? "#52c41a" : "#ff4d4f" }}>
            {passed ? "通过" : "未通过"}
          </Text>
          <div style={{ display: "flex", gap: 12, marginTop: 4 }}>
            <Text style={{ fontSize: 12 }}>
              总计: <Badge count={summary.total} color="#1890ff" style={{ fontSize: 10 }} showZero />
            </Text>
            <Text style={{ fontSize: 12 }}>
              错误: <Badge count={summary.errors} color="#ff4d4f" style={{ fontSize: 10 }} showZero />
            </Text>
            <Text style={{ fontSize: 12 }}>
              警告: <Badge count={summary.warnings} color="#fa8c16" style={{ fontSize: 10 }} showZero />
            </Text>
          </div>
        </div>
      </div>

      {/* Violations table */}
      <Text strong style={{ fontSize: 12 }}>违规列表</Text>
      {violations.length === 0 ? (
        <Empty description="无违规" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Table<DrcViolation>
          dataSource={violations}
          columns={columns}
          size="small"
          pagination={{ pageSize: 10, size: "small" }}
          rowKey={(r) => `${r.rule_id}-${r.polygon_id}-${r.location.join(",")}`}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: {
              cursor: "pointer",
              background: highlightedViolationPolygonId === record.polygon_id
                ? (record.severity === "error" ? "#fff1f0" : "#fff7e6")
                : undefined,
            },
          })}
          rowClassName={(record) =>
            highlightedViolationPolygonId === record.polygon_id ? "drc-row-selected" : ""
          }
          scroll={{ x: true }}
        />
      )}
    </div>
  );
}
