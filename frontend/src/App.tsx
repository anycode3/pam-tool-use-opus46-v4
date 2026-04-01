import { Layout, Typography, Spin, Alert } from "antd";
import FileUpload from "./components/FileUpload";
import ProjectList from "./components/ProjectList";
import LayoutViewer from "./components/LayoutViewer";
import LayerPanel from "./components/LayerPanel";
import DevicePanel from "./components/DevicePanel";
import { useProjectStore } from "./store/useProjectStore";

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

export default function App() {
  const { loading, error, clearError, currentProject } = useProjectStore();

  return (
    <Layout style={{ height: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          background: "#001529",
          padding: "0 24px",
        }}
      >
        <Title level={4} style={{ color: "#fff", margin: 0 }}>
          PAM 版图优化工具
        </Title>
        {currentProject && (
          <Typography.Text style={{ color: "#aaa" }}>
            当前: {currentProject.name}
          </Typography.Text>
        )}
        {loading && <Spin size="small" />}
      </Header>

      {error && (
        <Alert
          message={error}
          type="error"
          closable
          onClose={clearError}
          style={{ margin: 0 }}
        />
      )}

      <Layout style={{ flex: 1, overflow: "hidden" }}>
        <Sider width={280} theme="light" style={{ padding: 12, overflowY: "auto" }}>
          <FileUpload />
          <div style={{ marginTop: 16 }}>
            <Typography.Text strong>项目列表</Typography.Text>
            <ProjectList />
          </div>
          <LayerPanel />
        </Sider>

        <Content style={{ position: "relative", background: "#1a1a2e" }}>
          <LayoutViewer />
        </Content>

        <Sider
          width={300}
          theme="light"
          style={{ overflowY: "auto", borderLeft: "1px solid #f0f0f0" }}
        >
          <DevicePanel />
        </Sider>
      </Layout>
    </Layout>
  );
}
