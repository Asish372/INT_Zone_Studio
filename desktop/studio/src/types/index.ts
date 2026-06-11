export type ThemeMode = "system" | "light" | "dark";

export type MenuTab =
  | "Home"
  | "Detection"
  | "Review"
  | "View"
  | "INT Zones"
  | "Help";

export type PanelId =
  | "explorer"
  | "table"
  | "properties"
  | "validation"
  | "audit"
  | "console"
  | "minimap";

export type WorkspaceLayoutName =
  | "default"
  | "review"
  | "detection"
  | "export";

export type StudioCommandId =
  | "file.newProject"
  | "file.openProject"
  | "file.openRecent"
  | "file.importDxf"
  | "file.importDwg"
  | "file.importSeed"
  | "file.importValidation"
  | "file.save"
  | "file.saveAs"
  | "file.saveVersion"
  | "file.autoSave"
  | "file.projectSettings"
  | "file.projectProperties"
  | "file.projectStatistics"
  | "file.closeDrawing"
  | "file.closeProject"
  | "file.exit"
  | "edit.copy"
  | "edit.paste"
  | "edit.duplicate"
  | "edit.undo"
  | "edit.redo"
  | "tool.select"
  | "tool.rectSelect"
  | "tool.lassoSelect"
  | "tool.multiSelect"
  | "view.pan"
  | "view.zoomWindow"
  | "view.fit"
  | "view.zoomExtents"
  | "view.grid"
  | "view.coordinates"
  | "view.scaleBar"
  | "view.northArrow"
  | "view.polygonIds"
  | "view.polygonIds.selected"
  | "view.polygonIds.visible"
  | "view.polygonIds.all"
  | "view.areas"
  | "view.vertices"
  | "view.labels"
  | "view.cadDrawing"
  | "view.intZones"
  | "view.faces"
  | "view.obstacles"
  | "view.boundary"
  | "view.goToCoordinates"
  | "view.theme.dark"
  | "view.theme.light"
  | "view.theme.auto"
  | "panel.toggle.explorer"
  | "panel.toggle.table"
  | "panel.toggle.properties"
  | "panel.toggle.validation"
  | "panel.toggle.audit"
  | "panel.toggle.console"
  | "panel.toggle.layers"
  | "panel.toggle.minimap"
  | "detection.run"
  | "detection.rerun"
  | "detection.selection"
  | "detection.all"
  | "detection.defineSlabBoundary"
  | "detection.pickBoundary"
  | "detection.autoBoundary"
  | "detection.drawSlabBoundary"
  | "detection.editBoundary"
  | "detection.applyBoundary"
  | "detection.seedRecovery"
  | "detection.recoverMissing"
  | "polygon.drawManual"
  | "detection.bulkRecovery"
  | "detection.openBoundaries"
  | "detection.unclosed"
  | "detection.gapAnalysis"
  | "detection.stats.detected"
  | "detection.stats.missing"
  | "detection.stats.coverage"
  | "polygon.select"
  | "polygon.selectSimilar"
  | "polygon.selectByArea"
  | "polygon.selectByLayer"
  | "polygon.delete"
  | "polygon.merge"
  | "polygon.split"
  | "polygon.moveVertex"
  | "polygon.addVertex"
  | "polygon.deleteVertex"
  | "polygon.approve"
  | "polygon.reject"
  | "polygon.needsReview"
  | "polygon.find"
  | "polygon.filter"
  | "zones.generate"
  | "zones.rebuild"
  | "zones.optimize"
  | "zones.merge"
  | "zones.split"
  | "zones.rename"
  | "zones.area"
  | "zones.count"
  | "zones.polygonCount"
  | "zones.showColors"
  | "zones.showLabels"
  | "zones.showBoundaries"
  | "review.mode"
  | "review.overlay"
  | "review.compare.detectedApproved"
  | "review.compare.autocad"
  | "review.compare.version"
  | "review.validate"
  | "review.errors"
  | "review.warnings"
  | "review.comment"
  | "review.resolveComment"
  | "review.issueTracker"
  | "review.approveDrawing"
  | "review.approveZone"
  | "review.approveProject"
  | "export.open"
  | "export.dxf"
  | "export.dwg"
  | "export.pdf"
  | "export.png"
  | "export.csv"
  | "export.excel"
  | "export.json"
  | "export.zonesDxf"
  | "export.clientPackage"
  | "export.reviewPackage"
  | "export.fullPackage"
  | "tools.measure.distance"
  | "tools.measure.area"
  | "tools.measure.angle"
  | "tools.measure.perimeter"
  | "tools.findDuplicates"
  | "tools.cleanGeometry"
  | "tools.repairGaps"
  | "tools.batch.detect"
  | "tools.batch.export"
  | "tools.batch.validate"
  | "layout.default"
  | "layout.review"
  | "layout.detection"
  | "layout.export"
  | "layout.reset"
  | "layout.save"
  | "layout.load"
  | "palette.open"
  | "help.guide"
  | "help.tutorial"
  | "help.shortcuts"
  | "help.systemInfo"
  | "help.logs"
  | "help.debugReport"
  | "help.support"
  | "help.about"
  | "help.exportPilotFeedback";

export interface PanelVisibility {
  explorer: boolean;
  table: boolean;
  properties: boolean;
  validation: boolean;
  audit: boolean;
  console: boolean;
  minimap: boolean;
}

export type PolygonIdMode = "off" | "selected" | "visible" | "all";

export interface CanvasOverlays {
  grid: boolean;
  coordinates: boolean;
  scaleBar: boolean;
  northArrow: boolean;
  polygonIdMode: PolygonIdMode;
  areas: boolean;
  vertices: boolean;
  labels: boolean;
}

export interface StudioCommandMeta {
  id: StudioCommandId;
  label: string;
  category: string;
  keywords?: string[];
  shortcut?: string;
}

export type ToolName =
  | "select"
  | "rect-select"
  | "add"
  | "scope-pick"
  | "scope-auto"
  | "scope-draw"
  | "scope-edit"
  | "manual-draw"
  | "pan"
  | "zoom-window";

export interface CadBoundaryCandidate {
  ring: [number, number][];
  layer: string;
  entity_handle: string;
  entity_type: string;
  area_m2: number;
}

export type SlabBoundarySource = "drawn" | "cad_pick" | "auto_layer";

export interface SlabBoundary {
  ring: [number, number][];
  area_m2: number;
  perimeter_m: number;
  centroid: [number, number];
  source: SlabBoundarySource;
  defined_at?: string;
  defined_by?: string;
  cad_ref?: {
    layer: string;
    entity_handle: string;
    entity_type: string;
  };
  auto_layer?: string;
}

export interface ObstacleFootprint {
  ring: [number, number][];
  area_m2?: number;
  centroid?: [number, number];
  layer?: string;
  block_name?: string;
  source?: string;
}

export interface WorkspaceScopeObstacles {
  footprints?: ObstacleFootprint[];
  classified_count?: number;
  appended_count?: number;
  footprint_count?: number;
}

export interface WorkspaceScope {
  boundary: SlabBoundary | null;
  detection_scoped?: boolean;
  boundary_stale?: boolean;
  obstacles?: WorkspaceScopeObstacles | null;
}

export type ReviewStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "needs_review";

export type UserRole = "engineer" | "reviewer" | "manager";

export type PolygonFilter =
  | "all"
  | "auto"
  | "recovered"
  | "manual"
  | "deleted"
  | "large"
  | "small"
  | "approved"
  | "pending"
  | "rejected";

export interface PolygonRecord {
  id: number;
  source: "auto" | "seed" | "manual" | string;
  status: string;
  review_status?: string;
  layer?: string;
  ring: [number, number][];
  area_m2: number;
  perimeter_m: number;
  centroid: [number, number];
  created_by?: string;
  int_zone?: string | null;
  scope_excluded?: boolean;
  geometry_role?: "partition" | "obstacle";
  obstacle_source?: string;
  obstacle_layer?: string;
}

export interface SceneData {
  cad_lines: [number, number, number, number][];
  polygons: PolygonRecord[];
  unit_label?: string;
  scope_boundary?: SlabBoundary | null;
}

export interface Counts {
  detected: number;
  seed_added: number;
  manual_added?: number;
  deleted: number;
  scope_excluded?: number;
  obstacles?: number;
  total: number;
}

export interface ActionEntry {
  message: string;
  kind: string;
  at: string;
  user?: string;
}

export interface Summary {
  session_id: string;
  source_file: string;
  unit_label: string;
  counts: Counts;
  selected_id: number | null;
  selected_ids?: number[];
  expected_polygon_count?: number | null;
  current_user?: string;
  current_role?: string;
  zones?: IntZone[];
  validation?: ValidationResult | null;
  project_id?: string | null;
  workspace_save_path?: string | null;
  cad_available?: boolean;
  scope?: WorkspaceScope;
  scope_enabled?: boolean;
  actions: ActionEntry[];
}

export interface WorkspaceSaveResult {
  path: string;
  relative_path?: string;
  actions: ActionEntry[];
}

export interface ExportSummary {
  file_count: number;
  formats: string[];
  polygon_count: number;
}

export interface ExportResult {
  ok?: boolean;
  polygon_count?: number;
  paths: Record<string, string>;
  absolute_paths?: Record<string, string>;
  folder?: string;
  summary?: ExportSummary;
  actions: ActionEntry[];
}

export interface SuspectedGapRegion {
  id: string;
  center: [number, number];
  seed_point: [number, number];
  bbox: [number, number, number, number];
  gap_distance: number | null;
  status: string;
  failure_reason: string | null;
  recoverable: boolean;
  priority: number;
  confidence: number;
  area_estimate_m2: number | null;
}

export interface SeedPreview {
  ring: [number, number][];
  area_m2: number;
  perimeter_m: number;
  centroid: [number, number];
}

export interface LayerVisibility {
  cad: boolean;
  zones: boolean;
  faces: boolean;
  obstacles: boolean;
  boundary: boolean;
  labels: boolean;
}

export interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export interface ValidationCounts {
  open_boundaries: number;
  self_intersections: number;
  gaps: number;
  overlaps: number;
  duplicates: number;
  tiny_polygons: number;
}

export interface ValidationIssue {
  type: string;
  polygon_id?: number;
  related_id?: number;
  severity: string;
  message: string;
}

export interface ValidationResult {
  ok: boolean;
  counts: ValidationCounts;
  issues: ValidationIssue[];
  validated_at?: string;
  suspected_gaps?: SuspectedGapRegion[];
  gap_summary?: {
    total: number;
    recoverable: number;
    informational: number;
  };
}

export interface IntZone {
  label: string;
  area_m2: number;
  face_count: number;
  polygon_ids: number[];
}

export interface ProjectMeta {
  id: string;
  name: string;
  created_at: string;
  drawings: { id: string; name: string }[];
  versions: {
    id: string;
    label: string;
    source_file: string;
    saved_at: string;
    polygon_count: number;
  }[];
  current_version?: string;
}

export interface Markup {
  id: number;
  x: number;
  y: number;
  text: string;
  user: string;
  at: string;
}

export interface Comment {
  user: string;
  text: string;
  at: string;
}
