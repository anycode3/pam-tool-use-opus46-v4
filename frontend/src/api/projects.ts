import apiClient from "./client";
import type { ProjectInfo, LayoutData, LayerInfo, Device, Modification, DiffChange } from "../types";

export async function uploadFile(file: File): Promise<ProjectInfo> {
  const formData = new FormData();
  formData.append("file", file);
  const resp = await apiClient.post("/api/projects/upload", formData);
  return resp.data;
}

export async function listProjects(): Promise<ProjectInfo[]> {
  const resp = await apiClient.get("/api/projects");
  return resp.data;
}

export async function getProject(id: string): Promise<ProjectInfo> {
  const resp = await apiClient.get(`/api/projects/${id}`);
  return resp.data;
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/api/projects/${id}`);
}

export async function getLayout(
  id: string,
  layers?: number[]
): Promise<LayoutData> {
  const params: Record<string, string> = {};
  if (layers && layers.length > 0) {
    params.layers = layers.join(",");
  }
  const resp = await apiClient.get(`/api/projects/${id}/layout`, { params });
  return resp.data;
}

export async function getLayers(id: string): Promise<{ layers: LayerInfo[] }> {
  const resp = await apiClient.get(`/api/projects/${id}/layers`);
  return resp.data;
}

export async function getLayerMapping(id: string): Promise<{ mappings: Record<string, string> }> {
  const resp = await apiClient.get(`/api/projects/${id}/layer-mapping`);
  return resp.data;
}

export async function saveLayerMapping(
  id: string,
  mappings: Record<string, string>
): Promise<{ mappings: Record<string, string> }> {
  const resp = await apiClient.put(`/api/projects/${id}/layer-mapping`, { mappings });
  return resp.data;
}

export async function recognizeDevices(
  id: string,
  method = "geometry"
): Promise<{ devices: Device[]; stats: Record<string, number> }> {
  const resp = await apiClient.post(`/api/projects/${id}/devices/recognize`, { method });
  return resp.data;
}

export async function getDevices(id: string): Promise<{ devices: Device[] }> {
  const resp = await apiClient.get(`/api/projects/${id}/devices`);
  return resp.data;
}

export async function getDevice(id: string, deviceId: string): Promise<Device> {
  const resp = await apiClient.get(`/api/projects/${id}/devices/${deviceId}`);
  return resp.data;
}

export async function modifyDevice(
  projectId: string,
  deviceId: string,
  params: { new_value: number; mode: string; manual_params?: Record<string, number> }
): Promise<Modification> {
  const resp = await apiClient.post(`/api/projects/${projectId}/devices/${deviceId}/modify`, params);
  return resp.data;
}

export async function applyModifications(
  projectId: string,
  modificationIds: string[]
): Promise<{ status: string; download_url: string }> {
  const resp = await apiClient.post(`/api/projects/${projectId}/apply-modifications`, { modifications: modificationIds });
  return resp.data;
}

export async function getDiff(projectId: string): Promise<{ changes: DiffChange[] }> {
  const resp = await apiClient.get(`/api/projects/${projectId}/diff`);
  return resp.data;
}

export async function downloadLayout(projectId: string): Promise<Blob> {
  const resp = await apiClient.get(`/api/projects/${projectId}/download`, { responseType: "blob" });
  return resp.data;
}
