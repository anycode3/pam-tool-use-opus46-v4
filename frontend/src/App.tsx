import { Layout, Typography, Spin, Alert, Tabs } from "antd";
import FileUpload from "./components/FileUpload";
import ProjectList from "./components/ProjectList";
import LayoutViewer from "./components/LayoutViewer";
import LayerPanel from "./components/LayerPanel";
import DevicePanel from "./components/DevicePanel";
import DrcRulesPanel from "./components/DrcRulesPanel";
import DrcResultsPanel from "./components/DrcResultsPanel";
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
          width={340}
          theme="light"
          style={{ borderLeft: "1px solid #f0f0f0", display: "flex", flexDirection: "column" }}
        >
          <Tabs
            defaultActiveKey="devices"
            size="small"
            style={{ height: "100%", display: "flex", flexDirection: "column" }}
            tabBarStyle={{ marginBottom: 0, paddingLeft: 12, paddingRight: 12, flexShrink: 0 }}
            items={[
              {
                key: "devices",
                label: "器件",
                children: (
                  <div style={{ overflowY: "auto", height: "calc(100vh - 120px)" }}>
                    <DevicePanel />
                  </div>
                ),
              },
              {
                key: "drc",
                label: "DRC",
                children: (
                  <div style={{ overflowY: "auto", height: "calc(100vh - 120px)" }}>
                    <DrcRulesPanel />
                    <DrcResultsPanel />
                  </div>
                ),
              },
            ]}
          />
        </Sider>
      </Layout>
    </Layout>
  );
}
