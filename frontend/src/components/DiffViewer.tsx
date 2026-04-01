import { Button, Table, Typography, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useProjectStore } from "../store/useProjectStore";
import type { DiffChange } from "../types";

const { Text } = Typography;

export default function DiffViewer() {
  const { diffChanges, fetchDiff, modifications, loading } = useProjectStore();

  if (modifications.length === 0) return null;

  const areaChange = (row: DiffChange): number => {
    if (row.old_area === 0) return 0;
    return ((row.new_area - row.old_area) / row.old_area) * 100;
  };

  const columns: ColumnsType<DiffChange> = [
    {
      title: "多边形 ID",
      dataIndex: "polygon_id",
      key: "polygon_id",
      ellipsis: true,
      render: (v: string) => (
        <Text style={{ fontSize: 11 }} copyable={{ text: v }}>
          {v.length > 12 ? `…${v.slice(-10)}` : v}
        </Text>
      ),
    },
    {
      title: "旧面积",
      dataIndex: "old_area",
      key: "old_area",
      render: (v: number) => <Text style={{ fontSize: 11 }}>{v.toFixed(3)}</Text>,
    },
    {
      title: "新面积",
      dataIndex: "new_area",
      key: "new_area",
      render: (v: number) => <Text style={{ fontSize: 11 }}>{v.toFixed(3)}</Text>,
    },
    {
      title: "变化 %",
      key: "change",
      render: (_: unknown, row: DiffChange) => {
        const pct = areaChange(row);
        const color = pct > 0 ? "green" : pct < 0 ? "red" : "default";
        return (
          <Tag color={color} style={{ fontSize: 11 }}>
            {pct >= 0 ? "+" : ""}
            {pct.toFixed(1)}%
          </Tag>
        );
      },
    },
  ];

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
        <Text strong style={{ fontSize: 13 }}>差异预览</Text>
        <Button size="small" onClick={fetchDiff} loading={loading}>
          加载差异
        </Button>
      </div>

      {diffChanges.length > 0 ? (
        <Table<DiffChange>
          dataSource={diffChanges}
          columns={columns}
          rowKey="polygon_id"
          size="small"
          pagination={{ pageSize: 5, size: "small", showSizeChanger: false }}
          style={{ fontSize: 11 }}
        />
      ) : (
        <Text type="secondary" style={{ fontSize: 12 }}>
          点击"加载差异"查看变更详情
        </Text>
      )}
    </div>
  );
}
