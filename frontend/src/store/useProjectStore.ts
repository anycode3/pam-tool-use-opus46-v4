import { create } from "zustand";
import type { ProjectInfo, LayoutData } from "../types";
import * as projectsApi from "../api/projects";

interface ProjectState {
  projects: ProjectInfo[];
  currentProject: ProjectInfo | null;
  layoutData: LayoutData | null;
  loading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  selectProject: (id: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  layoutData: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await projectsApi.listProjects();
      set({ projects, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  uploadFile: async (file: File) => {
    set({ loading: true, error: null });
    try {
      const project = await projectsApi.uploadFile(file);
      set((s) => ({
        projects: [...s.projects, project],
        currentProject: project,
        loading: false,
      }));
      await get().selectProject(project.id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  selectProject: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const [project, layoutData] = await Promise.all([
        projectsApi.getProject(id),
        projectsApi.getLayout(id),
      ]);
      set({ currentProject: project, layoutData, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  deleteProject: async (id: string) => {
    try {
      await projectsApi.deleteProject(id);
      set((s) => ({
        projects: s.projects.filter((p) => p.id !== id),
        currentProject: s.currentProject?.id === id ? null : s.currentProject,
        layoutData: s.currentProject?.id === id ? null : s.layoutData,
      }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg });
    }
  },

  clearError: () => set({ error: null }),
}));
