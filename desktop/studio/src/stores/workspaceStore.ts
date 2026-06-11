import { create } from "zustand";
import {
  createPolylineDraw,
  type PolylineDrawState,
} from "../viewer/polylineDraw";
import type {
  ActionEntry,
  CadBoundaryCandidate,
  CanvasOverlays,
  Comment,
  Counts,
  ExportResult,
  IntZone,
  LayerVisibility,
  Markup,
  MenuTab,
  PanelVisibility,
  PolygonIdMode,
  PolygonFilter,
  PolygonRecord,
  ProjectMeta,
  SceneData,
  SeedPreview,
  SlabBoundary,
  ToolName,
  UserRole,
  ValidationResult,
  WorkspaceLayoutName,
} from "../types";

const DEFAULT_PANELS: PanelVisibility = {
  explorer: true,
  table: true,
  properties: true,
  validation: false,
  audit: false,
  console: true,
  minimap: true,
};

const DEFAULT_LAYERS: LayerVisibility = {
  cad: true,
  zones: true,
  faces: true,
  obstacles: false,
  boundary: true,
  labels: true,
};

const DEFAULT_OVERLAYS: CanvasOverlays = {
  grid: false,
  coordinates: true,
  scaleBar: false,
  northArrow: false,
  polygonIdMode: "visible",
  areas: false,
  vertices: false,
  labels: true,
};

const LAYOUT_PRESETS: Record<WorkspaceLayoutName, PanelVisibility> = {
  default: { ...DEFAULT_PANELS },
  review: {
    explorer: true,
    table: true,
    properties: true,
    validation: true,
    audit: true,
    console: false,
    minimap: false,
  },
  detection: {
    explorer: true,
    table: false,
    properties: false,
    validation: true,
    audit: false,
    console: true,
    minimap: true,
  },
  export: {
    explorer: true,
    table: true,
    properties: true,
    validation: false,
    audit: false,
    console: false,
    minimap: false,
  },
};

interface WorkspaceState {
  screen: "welcome" | "workspace";
  sessionId: string;
  sourceFile: string;
  unitLabel: string;
  scene: SceneData | null;
  counts: Counts;
  actions: ActionEntry[];
  selectedId: number | null;
  selectedIds: number[];
  selectedPolygon: PolygonRecord | null;
  hoverId: number | null;
  tool: ToolName;
  layers: LayerVisibility;
  coords: { x: number; y: number };
  seedPreview: SeedPreview | null;
  seedClick: { x: number; y: number } | null;
  exportOpen: boolean;
  layerManagerOpen: boolean;
  settingsOpen: boolean;
  tableCollapsed: boolean;
  engineError: string | null;
  polygonFilter: PolygonFilter;
  polygonSearch: string;
  validation: ValidationResult | null;
  zones: IntZone[];
  selectedZone: string | null;
  reviewMode: boolean;
  comparisonOverlay: boolean;
  expectedPolygonCount: number | null;
  currentUser: string;
  currentRole: UserRole;
  projects: ProjectMeta[];
  activeProjectId: string | null;
  markups: Markup[];
  comments: Record<number, Comment[]>;
  showVertices: boolean;
  activeMenuTab: MenuTab;
  commandPaletteOpen: boolean;
  goToOpen: boolean;
  goToMode: "polygon" | "coordinates";
  panelVisibility: PanelVisibility;
  canvasOverlays: CanvasOverlays;
  workspaceLayout: WorkspaceLayoutName;
  studioToast: string | null;
  workspaceSavePath: string | null;
  cadAvailable: boolean;
  saveWorkspaceOpen: boolean;
  saveWorkspaceAs: boolean;
  exportSuccessOpen: boolean;
  lastExportResult: ExportResult | null;
  scopeEnabled: boolean;
  polylineDraw: PolylineDrawState | null;
  boundaryPreview: SlabBoundary | null;
  boundaryCadCandidates: CadBoundaryCandidate[];
  boundaryPickHover: CadBoundaryCandidate | null;
  boundaryEditRing: [number, number][] | null;
  boundarySnapKind: "endpoint" | "intersection" | "boundary_vertex" | null;
  manualPolygonPreview: SeedPreview | null;
  setScopeEnabled: (enabled: boolean) => void;
  setPolylineDraw: (state: PolylineDrawState | null) => void;
  setBoundaryPreview: (preview: SlabBoundary | null) => void;
  setBoundaryCadCandidates: (candidates: CadBoundaryCandidate[]) => void;
  setBoundaryPickHover: (candidate: CadBoundaryCandidate | null) => void;
  setBoundaryEditRing: (ring: [number, number][] | null) => void;
  setBoundarySnapKind: (
    kind: "endpoint" | "intersection" | "boundary_vertex" | null,
  ) => void;
  setManualPolygonPreview: (preview: SeedPreview | null) => void;
  clearScopeDraw: () => void;
  clearManualDraw: () => void;
  setWorkspaceSavePath: (path: string | null) => void;
  setCadAvailable: (available: boolean) => void;
  setSaveWorkspaceOpen: (open: boolean, asMode?: boolean) => void;
  setExportSuccessOpen: (open: boolean) => void;
  setLastExportResult: (result: ExportResult | null) => void;
  setScreen: (s: "welcome" | "workspace") => void;
  setSessionId: (id: string) => void;
  setScene: (scene: SceneData | null) => void;
  setCounts: (counts: Counts) => void;
  setActions: (actions: ActionEntry[]) => void;
  setSourceFile: (name: string) => void;
  setUnitLabel: (u: string) => void;
  setSelected: (id: number | null, poly: PolygonRecord | null) => void;
  setSelectedIds: (ids: number[], poly?: PolygonRecord | null) => void;
  setHoverId: (id: number | null) => void;
  setTool: (tool: ToolName) => void;
  setLayers: (layers: Partial<LayerVisibility>) => void;
  setCoords: (x: number, y: number) => void;
  setSeedPreview: (
    p: SeedPreview | null,
    click?: { x: number; y: number } | null,
  ) => void;
  setExportOpen: (open: boolean) => void;
  setLayerManagerOpen: (open: boolean) => void;
  setSettingsOpen: (open: boolean) => void;
  setTableCollapsed: (c: boolean) => void;
  setEngineError: (e: string | null) => void;
  setPolygonFilter: (f: PolygonFilter) => void;
  setPolygonSearch: (s: string) => void;
  setValidation: (v: ValidationResult | null) => void;
  setZones: (z: IntZone[]) => void;
  setSelectedZone: (label: string | null) => void;
  setReviewMode: (on: boolean) => void;
  setComparisonOverlay: (on: boolean) => void;
  setExpectedPolygonCount: (n: number | null) => void;
  setCurrentUser: (user: string, role: UserRole) => void;
  setProjects: (p: ProjectMeta[]) => void;
  setActiveProjectId: (id: string | null) => void;
  setMarkups: (m: Markup[]) => void;
  setComments: (polygonId: number, c: Comment[]) => void;
  setShowVertices: (show: boolean) => void;
  setActiveMenuTab: (tab: MenuTab) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setGoToOpen: (open: boolean, mode?: "polygon" | "coordinates") => void;
  togglePanel: (panel: keyof PanelVisibility) => void;
  setPanelVisibility: (panels: Partial<PanelVisibility>) => void;
  toggleCanvasOverlay: (key: keyof CanvasOverlays) => void;
  setCanvasOverlays: (overlays: Partial<CanvasOverlays>) => void;
  setPolygonIdMode: (mode: PolygonIdMode) => void;
  applyWorkspaceLayout: (layout: WorkspaceLayoutName) => void;
  setStudioToast: (msg: string | null) => void;
  resetWorkspace: () => void;
}

const defaultCounts: Counts = {
  detected: 0,
  seed_added: 0,
  manual_added: 0,
  deleted: 0,
  obstacles: 0,
  total: 0,
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  screen: "welcome",
  sessionId: "",
  sourceFile: "",
  unitLabel: "mm",
  scene: null,
  counts: defaultCounts,
  actions: [],
  selectedId: null,
  selectedIds: [],
  selectedPolygon: null,
  hoverId: null,
  tool: "select",
  layers: { ...DEFAULT_LAYERS },
  coords: { x: 0, y: 0 },
  seedPreview: null,
  seedClick: null,
  exportOpen: false,
  layerManagerOpen: false,
  settingsOpen: false,
  tableCollapsed: false,
  engineError: null,
  polygonFilter: "all",
  polygonSearch: "",
  validation: null,
  zones: [],
  selectedZone: null,
  reviewMode: false,
  comparisonOverlay: false,
  expectedPolygonCount: null,
  currentUser: "Engineer A",
  currentRole: "engineer",
  projects: [],
  activeProjectId: null,
  markups: [],
  comments: {},
  showVertices: false,
  activeMenuTab: "Detection",
  commandPaletteOpen: false,
  goToOpen: false,
  goToMode: "polygon",
  panelVisibility: { ...DEFAULT_PANELS },
  canvasOverlays: { ...DEFAULT_OVERLAYS },
  workspaceLayout: "default",
  studioToast: null,
  workspaceSavePath: null,
  cadAvailable: true,
  saveWorkspaceOpen: false,
  saveWorkspaceAs: false,
  exportSuccessOpen: false,
  lastExportResult: null,
  scopeEnabled: false,
  polylineDraw: null,
  boundaryPreview: null,
  boundaryCadCandidates: [],
  boundaryPickHover: null,
  boundaryEditRing: null,
  boundarySnapKind: null,
  manualPolygonPreview: null,
  setScopeEnabled: (scopeEnabled) => set({ scopeEnabled }),
  setPolylineDraw: (polylineDraw) => set({ polylineDraw }),
  setBoundaryPreview: (boundaryPreview) => set({ boundaryPreview }),
  setBoundaryCadCandidates: (boundaryCadCandidates) => set({ boundaryCadCandidates }),
  setBoundaryPickHover: (boundaryPickHover) => set({ boundaryPickHover }),
  setBoundaryEditRing: (boundaryEditRing) => set({ boundaryEditRing }),
  setBoundarySnapKind: (boundarySnapKind) => set({ boundarySnapKind }),
  setManualPolygonPreview: (manualPolygonPreview) => set({ manualPolygonPreview }),
  clearScopeDraw: () =>
    set({
      polylineDraw: null,
      boundaryPreview: null,
      boundaryPickHover: null,
      boundaryEditRing: null,
      boundarySnapKind: null,
    }),
  clearManualDraw: () =>
    set({ polylineDraw: null, manualPolygonPreview: null }),
  setWorkspaceSavePath: (workspaceSavePath) => set({ workspaceSavePath }),
  setCadAvailable: (cadAvailable) => set({ cadAvailable }),
  setSaveWorkspaceOpen: (saveWorkspaceOpen, asMode = false) =>
    set({ saveWorkspaceOpen, saveWorkspaceAs: asMode }),
  setExportSuccessOpen: (exportSuccessOpen) => set({ exportSuccessOpen }),
  setLastExportResult: (lastExportResult) => set({ lastExportResult }),
  setScreen: (screen) => set({ screen }),
  setSessionId: (sessionId) => set({ sessionId }),
  setScene: (scene) => set({ scene }),
  setCounts: (counts) => set({ counts }),
  setActions: (actions) => set({ actions }),
  setSourceFile: (sourceFile) => set({ sourceFile }),
  setUnitLabel: (unitLabel) => set({ unitLabel }),
  setSelected: (selectedId, selectedPolygon) =>
    set({
      selectedId,
      selectedPolygon,
      selectedIds: selectedId != null ? [selectedId] : [],
    }),
  setSelectedIds: (selectedIds, selectedPolygon = null) =>
    set({
      selectedIds,
      selectedId: selectedIds[0] ?? null,
      selectedPolygon: selectedPolygon ?? null,
    }),
  setHoverId: (hoverId) => set({ hoverId }),
  setTool: (tool) =>
    set((s) => {
      const keepBoundaryState =
        tool === "select" ||
        tool === "scope-draw" ||
        tool === "scope-pick" ||
        tool === "scope-auto" ||
        tool === "scope-edit";
      return {
        tool,
        seedPreview: tool === "add" ? s.seedPreview : null,
        seedClick: tool === "add" ? s.seedClick : null,
        polylineDraw:
          tool === "scope-draw" || tool === "manual-draw"
            ? s.polylineDraw ?? createPolylineDraw()
            : null,
        boundaryPreview: keepBoundaryState ? s.boundaryPreview : null,
        boundaryPickHover: tool === "scope-pick" ? s.boundaryPickHover : null,
        boundaryEditRing: tool === "scope-edit" ? s.boundaryEditRing : null,
        boundarySnapKind: null,
        manualPolygonPreview: tool === "manual-draw" ? s.manualPolygonPreview : null,
      };
    }),
  setLayers: (partial) =>
    set((s) => {
      const layers = { ...s.layers, ...partial };
      const patch: Partial<typeof s> = { layers };
      if (partial.labels != null) {
        const mode: PolygonIdMode = partial.labels
          ? s.canvasOverlays.polygonIdMode === "off"
            ? "visible"
            : s.canvasOverlays.polygonIdMode
          : "off";
        patch.canvasOverlays = {
          ...s.canvasOverlays,
          polygonIdMode: mode,
          labels: partial.labels,
        };
      }
      return patch;
    }),
  setCoords: (x, y) => set({ coords: { x, y } }),
  setSeedPreview: (seedPreview, seedClick = null) =>
    set({ seedPreview, seedClick: seedClick ?? null }),
  setExportOpen: (exportOpen) => set({ exportOpen }),
  setLayerManagerOpen: (layerManagerOpen) => set({ layerManagerOpen }),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  setTableCollapsed: (tableCollapsed) => set({ tableCollapsed }),
  setEngineError: (engineError) => set({ engineError }),
  setPolygonFilter: (polygonFilter) => set({ polygonFilter }),
  setPolygonSearch: (polygonSearch) => set({ polygonSearch }),
  setValidation: (validation) => set({ validation }),
  setZones: (zones) => set({ zones }),
  setSelectedZone: (selectedZone) => set({ selectedZone }),
  setReviewMode: (reviewMode) => set({ reviewMode }),
  setComparisonOverlay: (comparisonOverlay) => set({ comparisonOverlay }),
  setExpectedPolygonCount: (expectedPolygonCount) =>
    set({ expectedPolygonCount }),
  setCurrentUser: (currentUser, currentRole) =>
    set({ currentUser, currentRole }),
  setProjects: (projects) => set({ projects }),
  setActiveProjectId: (activeProjectId) => set({ activeProjectId }),
  setMarkups: (markups) => set({ markups }),
  setComments: (polygonId, comments) =>
    set((s) => ({ comments: { ...s.comments, [polygonId]: comments } })),
  setShowVertices: (showVertices) => set({ showVertices }),
  setActiveMenuTab: (activeMenuTab) => set({ activeMenuTab }),
  setCommandPaletteOpen: (commandPaletteOpen) => set({ commandPaletteOpen }),
  setGoToOpen: (goToOpen, mode) =>
    set((s) => ({
      goToOpen,
      goToMode: mode ?? s.goToMode,
    })),
  togglePanel: (panel) =>
    set((s) => ({
      panelVisibility: {
        ...s.panelVisibility,
        [panel]: !s.panelVisibility[panel],
      },
    })),
  setPanelVisibility: (partial) =>
    set((s) => ({
      panelVisibility: { ...s.panelVisibility, ...partial },
    })),
  toggleCanvasOverlay: (key) =>
    set((s) => {
      if (key === "polygonIdMode") return s;
      const next = !s.canvasOverlays[key];
      const patch: Partial<typeof s> = {
        canvasOverlays: { ...s.canvasOverlays, [key]: next },
      };
      if (key === "vertices") patch.showVertices = next;
      if (key === "labels") {
        const mode: PolygonIdMode = next
          ? s.canvasOverlays.polygonIdMode === "off"
            ? "visible"
            : s.canvasOverlays.polygonIdMode
          : "off";
        patch.canvasOverlays = {
          ...s.canvasOverlays,
          labels: next,
          polygonIdMode: mode,
        };
        patch.layers = { ...s.layers, labels: next };
      }
      return patch;
    }),
  setCanvasOverlays: (partial) =>
    set((s) => {
      const canvasOverlays = { ...s.canvasOverlays, ...partial };
      const patch: Partial<typeof s> = { canvasOverlays };
      if (partial.vertices != null) patch.showVertices = partial.vertices;
      if (partial.labels != null) {
        patch.layers = { ...s.layers, labels: partial.labels };
        if (partial.polygonIdMode == null) {
          canvasOverlays.polygonIdMode = partial.labels
            ? s.canvasOverlays.polygonIdMode === "off"
              ? "visible"
              : s.canvasOverlays.polygonIdMode
            : "off";
        }
      }
      if (partial.polygonIdMode != null) {
        canvasOverlays.labels = partial.polygonIdMode !== "off";
        patch.layers = {
          ...s.layers,
          labels: partial.polygonIdMode !== "off",
        };
      }
      return patch;
    }),
  setPolygonIdMode: (mode) =>
    set((s) => ({
      canvasOverlays: {
        ...s.canvasOverlays,
        polygonIdMode: mode,
        labels: mode !== "off",
      },
      layers: { ...s.layers, labels: mode !== "off" },
    })),
  applyWorkspaceLayout: (workspaceLayout) =>
    set({
      workspaceLayout,
      panelVisibility: { ...LAYOUT_PRESETS[workspaceLayout] },
    }),
  setStudioToast: (studioToast) => set({ studioToast }),
  resetWorkspace: () =>
    set({
      scene: null,
      counts: defaultCounts,
      actions: [],
      selectedId: null,
      selectedIds: [],
      selectedPolygon: null,
      hoverId: null,
      seedPreview: null,
      seedClick: null,
      polylineDraw: null,
      boundaryPreview: null,
      boundaryCadCandidates: [],
      boundaryPickHover: null,
      boundaryEditRing: null,
      boundarySnapKind: null,
      manualPolygonPreview: null,
      validation: null,
      zones: [],
      markups: [],
      comments: {},
      workspaceSavePath: null,
      cadAvailable: true,
      saveWorkspaceOpen: false,
      saveWorkspaceAs: false,
    }),
}));
