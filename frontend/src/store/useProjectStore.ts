import { create } from "zustand";
import type { ProjectInfo, LayoutData, Device, Modification, DiffChange, DrcRule, DrcResults } from "../types";
import * as projectsApi from "../api/projects";

interface ProjectState {
  projects: ProjectInfo[];
  currentProject: ProjectInfo | null;
  layoutData: LayoutData | null;
  layerMapping: Record<string, string>;
  visibleLayers: Record<string, boolean>;
  devices: Device[];
  selectedDevice: Device | null;
  modifications: Modification[];
  diffChanges: DiffChange[];
  drcRules: DrcRule[];
  drcResults: DrcResults | null;
  highlightedViolationPolygonId: string | null;
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
  recognizeDevices: (projectId: string) => Promise<void>;
  selectDevice: (device: Device | null) => void;
  fetchDevices: (projectId: string) => Promise<void>;
  modifyDevice: (deviceId: string, newValue: number, mode: string, manualParams?: Record<string, number>) => Promise<void>;
  applyModifications: () => Promise<void>;
  fetchDiff: () => Promise<void>;
  downloadLayout: () => Promise<void>;
  clearModifications: () => void;
  saveDrcRules: (rules: DrcRule[]) => Promise<void>;
  fetchDrcRules: () => Promise<void>;
  runDrc: () => Promise<void>;
  fetchDrcResults: () => Promise<void>;
  setHighlightedViolationPolygonId: (id: string | null) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  layoutData: null,
  layerMapping: {},
  visibleLayers: {},
  devices: [],
  selectedDevice: null,
  modifications: [],
  diffChanges: [],
  drcRules: [],
  drcResults: null,
  highlightedViolationPolygonId: null,
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
      set({ currentProject: project, layoutData, visibleLayers, loading: false,
        devices: [], selectedDevice: null,
        modifications: [], diffChanges: [],
        drcResults: null, drcRules: [], highlightedViolationPolygonId: null,
      });
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
        devices: s.currentProject?.id === id ? [] : s.devices,
        selectedDevice: s.currentProject?.id === id ? null : s.selectedDevice,
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

  recognizeDevices: async (projectId: string) => {
    set({ loading: true, error: null });
    try {
      const { devices } = await projectsApi.recognizeDevices(projectId);
      set({ devices, selectedDevice: null, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  selectDevice: (device: Device | null) => {
    set({ selectedDevice: device });
  },

  fetchDevices: async (projectId: string) => {
    try {
      const { devices } = await projectsApi.getDevices(projectId);
      set({ devices });
    } catch {
      // Devices may not be recognized yet; silently ignore
    }
  },

  modifyDevice: async (deviceId: string, newValue: number, mode: string, manualParams?: Record<string, number>) => {
    const { currentProject } = get();
    if (!currentProject) return;
    set({ loading: true, error: null });
    try {
      const modification = await projectsApi.modifyDevice(currentProject.id, deviceId, {
        new_value: newValue,
        mode,
        manual_params: manualParams,
      });
      set((s) => ({ modifications: [...s.modifications, modification], loading: false }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  applyModifications: async () => {
    const { currentProject, modifications } = get();
    if (!currentProject || modifications.length === 0) return;
    set({ loading: true, error: null });
    try {
      await projectsApi.applyModifications(currentProject.id, modifications.map((m) => m.id));
      set({ loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  fetchDiff: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    set({ loading: true, error: null });
    try {
      const { changes } = await projectsApi.getDiff(currentProject.id);
      set({ diffChanges: changes, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  downloadLayout: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    set({ loading: true, error: null });
    try {
      const blob = await projectsApi.downloadLayout(currentProject.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${currentProject.name}_modified.gds`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      set({ loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  clearModifications: () => set({ modifications: [], diffChanges: [] }),

  saveDrcRules: async (rules: DrcRule[]) => {
    const { currentProject } = get();
    if (!currentProject) return;
    set({ loading: true, error: null });
    try {
      const { rules: saved } = await projectsApi.saveDrcRules(currentProject.id, rules);
      set({ drcRules: saved, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  fetchDrcRules: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    try {
      const { rules } = await projectsApi.getDrcRules(currentProject.id);
      set({ drcRules: rules });
    } catch {
      // DRC rules may not exist yet; silently ignore
    }
  },

  runDrc: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    set({ loading: true, error: null });
    try {
      const results = await projectsApi.runDrc(currentProject.id);
      set({ drcResults: results, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false });
    }
  },

  fetchDrcResults: async () => {
    const { currentProject } = get();
    if (!currentProject) return;
    try {
      const results = await projectsApi.getDrcResults(currentProject.id);
      set({ drcResults: results });
    } catch {
      // DRC results may not exist yet; silently ignore
    }
  },

  setHighlightedViolationPolygonId: (id: string | null) => {
    set({ highlightedViolationPolygonId: id });
  },
}));
