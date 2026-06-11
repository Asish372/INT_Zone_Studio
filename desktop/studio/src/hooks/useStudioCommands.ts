import { useCallback } from "react";
import {
  applyScopeBoundary,
  autoDetectScopeBoundary,
  createProject,
  deletePolygon,
  exportWorkspace,
  fetchBoundaryCadCandidates,
  fetchScene,
  generateZones,
  redo,
  reviewPolygon,
  runValidation,
  saveProjectVersion,
  saveWorkspace,
  undo,
} from "../api/engine";
import { exportPilotFeedbackTemplate } from "../lib/exportPilotFeedback";
import { clearPanelLayouts } from "../lib/panelLayout";
import { useTheme } from "./useTheme";
import { useWorkspaceStore } from "../stores/workspaceStore";
import type { PolygonRecord, StudioCommandId } from "../types";
import { isActiveWorkspacePolygon } from "../viewer/geometry";

export interface StudioCommandHandlers {
  onOpenProject: () => void;
  onImportDrawing: (format?: "dxf" | "dwg" | "any") => void;
  onRefresh: () => Promise<void>;
}

function hasManualEdits(counts: {
  seed_added: number;
  manual_added?: number;
  deleted: number;
}): boolean {
  return (
    counts.seed_added > 0 ||
    (counts.manual_added ?? 0) > 0 ||
    counts.deleted > 0
  );
}

function hasReviewedPolygons(polygons: PolygonRecord[] | undefined): boolean {
  if (!polygons?.length) return false;
  return polygons.some(
    (p) =>
      isActiveWorkspacePolygon(p) &&
      !!p.review_status &&
      p.review_status !== "pending",
  );
}

function needsApplyBoundaryConfirm(
  counts: { seed_added: number; deleted: number },
  polygons: PolygonRecord[] | undefined,
): boolean {
  return hasManualEdits(counts) || hasReviewedPolygons(polygons);
}

function confirmApplyBoundary(): boolean {
  return window.confirm(
    "Apply Boundary will rerun detection inside the slab boundary and replace current detection results. Recoveries, deletions, and review statuses may be lost. Continue?",
  );
}

function confirmRedetect(): boolean {
  return window.confirm(
    "Re-run detection will replace auto-detected polygons and may overwrite manual edits. Continue?",
  );
}

function toast(message: string) {
  const setStudioToast = useWorkspaceStore.getState().setStudioToast;
  setStudioToast(message);
  window.setTimeout(() => {
    if (useWorkspaceStore.getState().studioToast === message) {
      setStudioToast(null);
    }
  }, 2800);
}

function logAction(message: string, kind = "info") {
  const { actions, setActions } = useWorkspaceStore.getState();
  setActions([
    {
      message,
      kind,
      at: new Date().toISOString(),
    },
    ...actions,
  ]);
}

export function useStudioCommands(handlers: StudioCommandHandlers) {
  const { setMode } = useTheme();

  const executeCommand = useCallback(
    async (commandId: StudioCommandId) => {
      const s = useWorkspaceStore.getState();

      switch (commandId) {
        case "file.newProject": {
          const name = prompt("Project name:", "New Project");
          if (!name) return;
          try {
            const p = await createProject(name);
            s.setProjects([...s.projects, p]);
            s.setActiveProjectId(p.id);
            logAction(`Project created: ${name}`, "success");
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Create failed");
          }
          break;
        }
        case "file.openProject":
          handlers.onOpenProject();
          break;
        case "file.importDxf":
          handlers.onImportDrawing("dxf");
          break;
        case "file.importDwg":
          handlers.onImportDrawing("dwg");
          break;
        case "file.save": {
          if (!s.scene) {
            toast("Open or import a drawing first");
            return;
          }
          if (s.workspaceSavePath) {
            try {
              const data = await saveWorkspace(s.sessionId, s.workspaceSavePath);
              s.setWorkspaceSavePath(data.path);
              s.setActions(data.actions);
              logAction(`Workspace saved: ${data.path}`, "success");
              toast("Workspace saved");
            } catch (e) {
              s.setEngineError(e instanceof Error ? e.message : "Save failed");
            }
          } else {
            s.setSaveWorkspaceOpen(true, false);
          }
          break;
        }
        case "file.saveAs":
          if (!s.scene) {
            toast("Open or import a drawing first");
            return;
          }
          s.setSaveWorkspaceOpen(true, true);
          break;
        case "export.open":
          s.setExportOpen(true);
          break;
        case "file.saveVersion": {
          if (!s.activeProjectId) {
            toast("Create a project first (File → New Project)");
            return;
          }
          try {
            const p = await saveProjectVersion(s.sessionId, s.activeProjectId);
            s.setProjects(s.projects.map((x) => (x.id === p.id ? p : x)));
            logAction(`Version saved: ${p.current_version}`, "success");
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Save version failed");
          }
          break;
        }
        case "file.projectSettings":
          s.setSettingsOpen(true);
          break;
        case "edit.undo":
          try {
            const data = await undo(s.sessionId);
            s.setScene(data.scene);
            s.setCounts(data.counts);
            s.clearScopeDraw();
            logAction("Undo", "info");
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Undo failed");
          }
          break;
        case "edit.redo":
          try {
            const data = await redo(s.sessionId);
            s.setScene(data.scene);
            s.setCounts(data.counts);
            s.clearScopeDraw();
            logAction("Redo", "info");
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Redo failed");
          }
          break;
        case "tool.select":
          s.setTool("select");
          break;
        case "tool.rectSelect":
          s.setTool("rect-select");
          break;
        case "view.pan":
          s.setTool("pan");
          break;
        case "view.zoomWindow":
          s.setTool("zoom-window");
          break;
        case "view.fit":
        case "view.zoomExtents":
          window.dispatchEvent(new CustomEvent("studio:fit-view"));
          break;
        case "view.coordinates":
          s.toggleCanvasOverlay("coordinates");
          break;
        case "view.polygonIds":
        case "view.polygonIds.visible": {
          const current = useWorkspaceStore.getState().canvasOverlays.polygonIdMode;
          s.setPolygonIdMode(current === "visible" ? "off" : "visible");
          break;
        }
        case "view.polygonIds.selected": {
          const current = useWorkspaceStore.getState().canvasOverlays.polygonIdMode;
          s.setPolygonIdMode(current === "selected" ? "off" : "selected");
          break;
        }
        case "view.polygonIds.all": {
          const current = useWorkspaceStore.getState().canvasOverlays.polygonIdMode;
          s.setPolygonIdMode(current === "all" ? "off" : "all");
          break;
        }
        case "view.vertices":
          s.toggleCanvasOverlay("vertices");
          break;
        case "view.labels":
          s.setLayers({ labels: !useWorkspaceStore.getState().layers.labels });
          break;
        case "view.cadDrawing":
          s.setLayers({ cad: !useWorkspaceStore.getState().layers.cad });
          break;
        case "view.intZones":
          s.setLayers({ zones: !useWorkspaceStore.getState().layers.zones });
          break;
        case "view.faces":
          s.setLayers({ faces: !useWorkspaceStore.getState().layers.faces });
          break;
        case "view.obstacles":
          s.setLayers({ obstacles: !useWorkspaceStore.getState().layers.obstacles });
          break;
        case "view.boundary":
          s.setLayers({ boundary: !useWorkspaceStore.getState().layers.boundary });
          break;
        case "view.goToCoordinates":
          s.setGoToOpen(true, "coordinates");
          break;
        case "view.theme.dark":
          setMode("dark");
          break;
        case "view.theme.light":
          setMode("light");
          break;
        case "view.theme.auto":
          setMode("system");
          break;
        case "panel.toggle.explorer":
          s.togglePanel("explorer");
          break;
        case "panel.toggle.table":
          s.togglePanel("table");
          break;
        case "panel.toggle.properties":
          s.togglePanel("properties");
          break;
        case "panel.toggle.validation":
          s.togglePanel("validation");
          break;
        case "panel.toggle.audit":
          s.togglePanel("audit");
          break;
        case "panel.toggle.console":
          s.togglePanel("console");
          break;
        case "panel.toggle.minimap":
          s.togglePanel("minimap");
          break;
        case "panel.toggle.layers":
          s.setLayerManagerOpen(true);
          break;
        case "detection.run":
        case "detection.rerun":
        case "detection.all": {
          if (!s.cadAvailable) {
            toast("CAD source unavailable — import drawing to run detection");
            return;
          }
          if (
            (commandId === "detection.rerun" || commandId === "detection.all") &&
            hasManualEdits(s.counts) &&
            !confirmRedetect()
          ) {
            return;
          }
          await handlers.onRefresh();
          logAction("Detection refreshed", "success");
          break;
        }
        case "detection.defineSlabBoundary":
        case "detection.pickBoundary": {
          if (!s.scopeEnabled) return;
          if (!s.scene) {
            toast("Import a drawing before defining slab boundary");
            return;
          }
          if (!s.cadAvailable) {
            toast("CAD source required to pick boundary from drawing");
            return;
          }
          s.clearScopeDraw();
          try {
            const candidates = await fetchBoundaryCadCandidates(s.sessionId);
            s.setBoundaryCadCandidates(candidates);
            s.setTool("scope-pick");
            toast("Click a closed CAD polyline on the drawing");
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Could not load CAD boundaries");
          }
          break;
        }
        case "detection.autoBoundary": {
          if (!s.scopeEnabled) return;
          if (!s.scene) {
            toast("Import a drawing before auto-detecting boundary");
            return;
          }
          if (!s.cadAvailable) {
            toast("CAD source required for auto boundary detection");
            return;
          }
          s.clearScopeDraw();
          s.setTool("scope-auto");
          try {
            const preview = await autoDetectScopeBoundary(s.sessionId);
            s.setBoundaryPreview(preview);
            s.setTool("select");
            toast(`Auto boundary — ${preview.area_m2.toFixed(1)} m²`);
          } catch (e) {
            s.clearScopeDraw();
            s.setTool("select");
            s.setEngineError(e instanceof Error ? e.message : "Auto boundary failed");
          }
          break;
        }
        case "detection.drawSlabBoundary": {
          if (!s.scopeEnabled) return;
          if (!s.scene) {
            toast("Import a drawing before drawing slab boundary");
            return;
          }
          s.clearScopeDraw();
          s.setTool("scope-draw");
          toast("Draw boundary — click first point again to close");
          break;
        }
        case "detection.editBoundary": {
          if (!s.scopeEnabled) return;
          const ring = s.scene?.scope_boundary?.ring ?? s.boundaryPreview?.ring;
          if (!ring?.length) {
            toast("Define a boundary before editing vertices");
            return;
          }
          s.setBoundaryEditRing(ring.map((p) => [...p] as [number, number]));
          if (s.boundaryPreview) {
            s.setTool("scope-edit");
          } else if (s.scene?.scope_boundary) {
            s.setBoundaryPreview(s.scene.scope_boundary);
            s.setTool("scope-edit");
          }
          break;
        }
        case "detection.applyBoundary": {
          if (!s.scopeEnabled) return;
          if (!s.scene?.scope_boundary?.ring?.length) {
            toast("Define a slab boundary before applying");
            return;
          }
          if (!s.cadAvailable) {
            toast("CAD source unavailable — apply boundary requires CAD geometry");
            return;
          }
          if (
            needsApplyBoundaryConfirm(s.counts, s.scene?.polygons) &&
            !confirmApplyBoundary()
          ) {
            return;
          }
          try {
            const data = await applyScopeBoundary(s.sessionId);
            s.setScene(data.scene);
            s.setCounts(data.counts);
            s.setActions(data.actions);
            toast("Detection rerun inside slab boundary.");
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Apply boundary failed");
          }
          break;
        }
        case "detection.seedRecovery":
        case "detection.recoverMissing": {
          if (!s.cadAvailable) {
            toast("CAD source unavailable — seed recovery requires CAD geometry");
            return;
          }
          s.setTool("add");
          toast("Click on canvas to recover missing polygon");
          break;
        }
        case "polygon.drawManual": {
          if (!s.scene) {
            toast("Import a drawing before drawing a polygon");
            return;
          }
          s.clearManualDraw();
          s.setTool("manual-draw");
          toast("Click vertices to draw a manual polygon");
          break;
        }
        case "detection.stats.detected":
          toast(`Detected: ${s.counts.detected} polygons`);
          break;
        case "detection.stats.missing": {
          const expected = s.expectedPolygonCount;
          const missing =
            expected != null ? Math.max(0, expected - s.counts.total) : null;
          toast(
            missing != null
              ? `Missing: ${missing} (expected ${expected})`
              : "Set expected count in Review mode",
          );
          break;
        }
        case "detection.stats.coverage": {
          const expected = s.expectedPolygonCount;
          if (expected == null || expected === 0) {
            toast("Set expected polygon count for coverage %");
            return;
          }
          const pct = Math.round((s.counts.total / expected) * 100);
          toast(`Coverage: ${pct}% (${s.counts.total}/${expected})`);
          break;
        }
        case "polygon.delete": {
          if (s.selectedId == null) {
            toast("Select a polygon first");
            return;
          }
          try {
            const data = await deletePolygon(s.sessionId, s.selectedId);
            s.setScene(data.scene);
            s.setCounts(data.counts);
            s.setActions(data.actions);
            s.setSelected(null, null);
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Delete failed");
          }
          break;
        }
        case "polygon.approve":
        case "polygon.reject":
        case "polygon.needsReview": {
          if (s.selectedId == null) {
            toast("Select a polygon first");
            return;
          }
          const status =
            commandId === "polygon.approve"
              ? "approved"
              : commandId === "polygon.reject"
                ? "rejected"
                : "needs_review";
          try {
            const data = await reviewPolygon(s.sessionId, s.selectedId, status);
            s.setScene(data.scene);
            s.setActions(data.actions);
            s.setSelected(s.selectedId, data.polygon);
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Review failed");
          }
          break;
        }
        case "polygon.find":
          s.setGoToOpen(true, "polygon");
          break;
        case "polygon.filter":
          s.setTableCollapsed(false);
          toast("Use filters in Polygon Table");
          break;
        case "zones.generate":
        case "zones.rebuild":
          try {
            const data = await generateZones(s.sessionId);
            s.setZones(data.zones);
            s.setScene(data.scene);
            s.setActions(data.actions);
            logAction(
              `INT zones ${commandId === "zones.rebuild" ? "rebuilt" : "generated"}: ${data.zones.length}`,
              "success",
            );
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Zone generation failed");
          }
          break;
        case "zones.area":
        case "zones.count":
        case "zones.polygonCount": {
          const zones = s.zones;
          if (!zones.length) {
            toast("Generate zones first");
            return;
          }
          if (commandId === "zones.count") toast(`Zones: ${zones.length}`);
          else if (commandId === "zones.polygonCount")
            toast(`Polygons in zones: ${zones.reduce((n, z) => n + z.polygon_ids.length, 0)}`);
          else
            toast(
              `Total zone area: ${zones.reduce((a, z) => a + z.area_m2, 0).toFixed(1)} m²`,
            );
          break;
        }
        case "review.mode":
          s.setReviewMode(!s.reviewMode);
          break;
        case "review.overlay":
          s.setComparisonOverlay(!s.comparisonOverlay);
          break;
        case "review.validate": {
          if (!s.cadAvailable) {
            toast("CAD-based gap validation requires the original CAD source");
            return;
          }
          try {
            const data = await runValidation(s.sessionId);
            s.setValidation(data.validation);
            s.setActions(data.actions);
            s.togglePanel("validation");
          } catch (e) {
            s.setEngineError(e instanceof Error ? e.message : "Validation failed");
          }
          break;
        }
        case "review.errors":
        case "review.warnings": {
          const issues = s.validation?.issues ?? [];
          const filtered = issues.filter((i) =>
            commandId === "review.errors"
              ? i.severity === "error"
              : i.severity === "warning",
          );
          s.togglePanel("validation");
          toast(
            filtered.length
              ? `${filtered.length} ${commandId === "review.errors" ? "errors" : "warnings"}`
              : "No issues — run validation first",
          );
          break;
        }
        case "export.dxf":
          await quickExport(["dxf"]);
          break;
        case "export.pdf":
          await quickExport(["pdf"]);
          break;
        case "export.csv":
          await quickExport(["csv"]);
          break;
        case "export.excel":
          await quickExport(["xlsx"]);
          break;
        case "export.json":
          await quickExport(["json"]);
          break;
        case "export.zonesDxf":
          await quickExport(["zones_dxf"]);
          break;
        case "export.clientPackage":
        case "export.fullPackage":
          await quickExport(["package"]);
          break;
        case "layout.default":
          s.applyWorkspaceLayout("default");
          s.setActiveMenuTab("Home");
          break;
        case "layout.review":
          s.applyWorkspaceLayout("review");
          s.setActiveMenuTab("Review");
          s.setReviewMode(true);
          break;
        case "layout.detection":
          s.applyWorkspaceLayout("detection");
          s.setActiveMenuTab("Detection");
          break;
        case "layout.export":
          s.applyWorkspaceLayout("export");
          s.setActiveMenuTab("Home");
          break;
        case "layout.reset":
          s.applyWorkspaceLayout("default");
          clearPanelLayouts();
          window.dispatchEvent(new CustomEvent("studio:reset-panel-layout"));
          toast("Layout reset");
          break;
        case "palette.open":
          s.setCommandPaletteOpen(true);
          break;
        case "help.shortcuts":
          toast("S Select · P Pan · F Fit · Ctrl+G Go To · Ctrl+Shift+P Commands");
          break;
        case "help.systemInfo":
          toast(
            `Session ${s.sessionId.slice(0, 8)}… · ${s.counts.total} polygons · ${s.sourceFile || "no drawing"}`,
          );
          break;
        case "help.logs":
          s.setPanelVisibility({ console: true });
          break;
        case "help.about":
          toast("INT ZONE STUDIO");
          break;
        case "help.exportPilotFeedback":
          try {
            const mode = await exportPilotFeedbackTemplate();
            logAction(
              mode === "open"
                ? "Opened PILOT_FEEDBACK.md"
                : "Downloaded PILOT_FEEDBACK.md",
              "success",
            );
            toast(
              mode === "open"
                ? "Pilot feedback template opened"
                : "Pilot feedback template downloaded",
            );
          } catch (e) {
            s.setEngineError(
              e instanceof Error ? e.message : "Could not export feedback template",
            );
          }
          break;
        default:
          break;
      }
    },
    [handlers, setMode],
  );

  return { executeCommand };
}

async function quickExport(formats: string[]) {
  const s = useWorkspaceStore.getState();
  try {
    const data = await exportWorkspace(s.sessionId, formats);
    s.setActions(data.actions);
    s.setLastExportResult(data);
    s.setExportSuccessOpen(true);
  } catch (e) {
    s.setEngineError(e instanceof Error ? e.message : "Export failed");
  }
}

export async function refreshScene() {
  const s = useWorkspaceStore.getState();
  const data = await fetchScene(s.sessionId);
  s.setScene(data.scene);
  s.setCounts(data.summary.counts);
  s.setActions(data.summary.actions);
}
