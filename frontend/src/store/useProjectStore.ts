import { create } from "zustand";
import type { ProjectInfo, LayoutData } from "../types";
import * as projectsApi from "../api/projects";

interface ProjectState {
  projects: ProjectInfo[];
  currentProject: ProjectInfo | null;
  layoutData: LayoutData | null;
  layerMapping: Record<string, string>;
  visibleLayers: Record<string, boolean>;
  loading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  selectProject: (id: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  clearError: () => void;
  toggleLayerVisibility: (layerName: string) => void;
  setAllLayersVisible: () => void;
  setAllLayersHidden: () => void;
  fetchLayerMapping: (projectId: string) => Promise<void>;
  saveLayerMapping: (projectId: string, mappings: Record<string, string>) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  layoutData: null,
  layerMapping: {},
  visibleLayers: {},
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
      // Initialize all layers as visible
      const visibleLayers: Record<string, boolean> = {};
      for (const layer of layoutData.layers) {
        visibleLayers[layer.name] = true;
      }
      set({ currentProject: project, layoutData, visibleLayers, loading: false });
      // Fetch layer mapping in background (don't block loading)
      get().fetchLayerMapping(id).catch(() => {/* ignore errors */});
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
        layerMapping: s.currentProject?.id === id ? {} : s.layerMapping,
        visibleLayers: s.currentProject?.id === id ? {} : s.visibleLayers,
      }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg });
    }
  },

  clearError: () => set({ error: null }),

  toggleLayerVisibility: (layerName: string) => {
    set((s) => ({
      visibleLayers: {
        ...s.visibleLayers,
        [layerName]: !s.visibleLayers[layerName],
      },
    }));
  },

  setAllLayersVisible: () => {
    set((s) => {
      const visibleLayers: Record<string, boolean> = {};
      for (const key of Object.keys(s.visibleLayers)) {
        visibleLayers[key] = true;
      }
      return { visibleLayers };
    });
  },

  setAllLayersHidden: () => {
    set((s) => {
      const visibleLayers: Record<string, boolean> = {};
      for (const key of Object.keys(s.visibleLayers)) {
        visibleLayers[key] = false;
      }
      return { visibleLayers };
    });
  },

  fetchLayerMapping: async (projectId: string) => {
    try {
      const { mappings } = await projectsApi.getLayerMapping(projectId);
      set({ layerMapping: mappings });
    } catch {
      // Layer mapping may not exist yet; silently ignore
    }
  },

  saveLayerMapping: async (projectId: string, mappings: Record<string, string>) => {
    try {
      const { mappings: saved } = await projectsApi.saveLayerMapping(projectId, mappings);
      set({ layerMapping: saved });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg });
    }
  },
}));
