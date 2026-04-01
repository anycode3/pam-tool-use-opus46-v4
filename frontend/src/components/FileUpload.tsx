import { Upload, message } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";

const { Dragger } = Upload;

export default function FileUpload() {
  const { uploadFile, loading } = useProjectStore();

  const handleUpload = async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["gds", "gds2", "gdsii", "dxf"].includes(ext)) {
      message.error("仅支持 GDS 和 DXF 格式文件");
      return false;
    }
    try {
      await uploadFile(file);
      message.success(`${file.name} 上传解析成功`);
    } catch {
      message.error(`${file.name} 上传失败`);
    }
    return false;
  };

  return (
    <Dragger
      accept=".gds,.gds2,.gdsii,.dxf"
      showUploadList={false}
      beforeUpload={handleUpload}
      disabled={loading}
      style={{ padding: "20px" }}
    >
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">点击或拖拽版图文件到此区域上传</p>
      <p className="ant-upload-hint">支持 GDS、DXF 格式</p>
    </Dragger>
  );
}
