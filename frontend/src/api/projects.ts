import apiClient from "./client";
import type { ProjectInfo, LayoutData } from "../types";

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
