import { useEffect } from "react";
import { List, Button, Typography, Popconfirm, Tag, Empty } from "antd";
import { DeleteOutlined, FolderOpenOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";

const { Text } = Typography;

export default function ProjectList() {
  const {
    projects,
    currentProject,
    fetchProjects,
    selectProject,
    deleteProject,
  } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  if (projects.length === 0) {
    return <Empty description="暂无项目" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <List
      size="small"
      dataSource={projects}
      renderItem={(item) => (
        <List.Item
          style={{
            cursor: "pointer",
            backgroundColor:
              currentProject?.id === item.id ? "#e6f4ff" : undefined,
            padding: "8px 12px",
          }}
          onClick={() => selectProject(item.id)}
          actions={[
            <Popconfirm
              title="确定删除此项目？"
              onConfirm={(e) => {
                e?.stopPropagation();
                deleteProject(item.id);
              }}
              onCancel={(e) => e?.stopPropagation()}
              key="delete"
            >
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={(e) => e.stopPropagation()}
              />
            </Popconfirm>,
          ]}
        >
          <List.Item.Meta
            avatar={<FolderOpenOutlined style={{ fontSize: 18 }} />}
            title={<Text ellipsis={{ tooltip: item.name }}>{item.name}</Text>}
            description={
              <span>
                <Tag color={item.file_type === "gds" ? "blue" : "green"}>
                  {item.file_type.toUpperCase()}
                </Tag>
                {item.geometry_count != null && (
                  <Text type="secondary">{item.geometry_count} 个图形</Text>
                )}
              </span>
            }
          />
        </List.Item>
      )}
    />
  );
}
