import { useState } from "react";
import { Modal, Upload, List, Tag, Typography, Space } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd/es/upload/interface";
import type { SpiceDevice } from "../types";

const { Text } = Typography;

interface Props {
  open: boolean;
  onClose: () => void;
  projectId: string;
}

const DEVICE_TYPE_COLORS: Record<string, "blue" | "green" | "orange"> = {
  inductor: "blue",
  capacitor: "green",
  resistor: "orange",
};

export default function NetlistUploadDialog({ open, onClose, projectId }: Props) {
  const [devices, setDevices] = useState<SpiceDevice[]>([]);
  const [uploading, setUploading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const resp = await fetch(`/api/projects/${projectId}/netlist/upload`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) throw new Error("Upload failed");
      const data = await resp.json();
      setDevices(data.devices ?? []);
    } catch {
      setDevices([]);
    } finally {
      setUploading(false);
    }
    return false; // prevent default upload behavior
  };

  const handleClose = () => {
    setDevices([]);
    setFileList([]);
    onClose();
  };

  return (
    <Modal
      title="上传网表"
      open={open}
      onOk={handleClose}
      onCancel={handleClose}
      okText="关闭"
      cancelText="取消"
      width={560}
      footer={null}
    >
      {devices.length === 0 ? (
        <Upload.Dragger
          name="file"
          fileList={fileList}
          onChange={({ fileList: fl }) => setFileList(fl)}
          beforeUpload={handleUpload}
          accept=".spice,.cir,.net"
          showUploadList={{ showRemoveIcon: false }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽上传网表文件</p>
          <p className="ant-upload-hint">支持 .spice, .cir, .net 格式</p>
        </Upload.Dragger>
      ) : (
        <List
          dataSource={devices}
          renderItem={(device) => (
            <List.Item>
              <Space direction="vertical" size={2}>
                <Space>
                  <Tag color={DEVICE_TYPE_COLORS[device.device_type] ?? "default"}>
                    {device.device_type}
                  </Tag>
                  <Text strong>{device.instance_name}</Text>
                </Space>
                <Text type="secondary">
                  {device.value} {device.unit}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  端口: {device.nets.join(", ")}
                </Text>
              </Space>
            </List.Item>
          )}
        />
      )}
    </Modal>
  );
}
