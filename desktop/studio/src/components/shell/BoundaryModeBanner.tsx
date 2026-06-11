import {
  applyScopeBoundary,
  autoDetectScopeBoundary,
  commitScopeBoundary,
  clearScopeBoundary,
} from "../../api/engine";
import type { PolygonRecord, SlabBoundary } from "../../types";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import { isActiveWorkspacePolygon } from "../../viewer/geometry";
import {
  liveDrawRing,
  ringAreaM2,
  ringPerimeter,
} from "../../viewer/polylineDraw";

function needsApplyBoundaryConfirm(
  counts: { seed_added: number; manual_added?: number; deleted: number },
  polygons: PolygonRecord[] | undefined,
): boolean {
  const manual =
    counts.seed_added > 0 || (counts.manual_added ?? 0) > 0 || counts.deleted > 0;
  const reviewed =
    polygons?.some(
      (p) => isActiveWorkspacePolygon(p) && !!p.review_status && p.review_status !== "pending",
    ) ?? false;
  return manual || reviewed;
}

function confirmApplyBoundary(): boolean {
  return window.confirm(
    "Apply Boundary will rerun detection inside the slab boundary and replace current detection results. Recoveries, deletions, and review statuses may be lost. Continue?",
  );
}

function formatMetrics(boundary: SlabBoundary) {
  return `${boundary.area_m2.toFixed(1)} m² · ${boundary.perimeter_m.toFixed(1)} m perimeter`;
}

export function BoundaryModeBanner() {
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const tool = useWorkspaceStore((s) => s.tool);
  const boundaryPreview = useWorkspaceStore((s) => s.boundaryPreview);
  const polylineDraw = useWorkspaceStore((s) => s.polylineDraw);
  const boundaryEditRing = useWorkspaceStore((s) => s.boundaryEditRing);
  const scene = useWorkspaceStore((s) => s.scene);
  const counts = useWorkspaceStore((s) => s.counts);
  const cadAvailable = useWorkspaceStore((s) => s.cadAvailable);
  const unitLabel = useWorkspaceStore((s) => s.unitLabel);
  const setTool = useWorkspaceStore((s) => s.setTool);
  const setBoundaryPreview = useWorkspaceStore((s) => s.setBoundaryPreview);
  const setBoundaryEditRing = useWorkspaceStore((s) => s.setBoundaryEditRing);
  const setScene = useWorkspaceStore((s) => s.setScene);
  const setCounts = useWorkspaceStore((s) => s.setCounts);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const clearScopeDraw = useWorkspaceStore((s) => s.clearScopeDraw);

  const unitScaleM = unitLabel === "m" ? 1 : 0.001;
  const hasSavedBoundary = Boolean(scene?.scope_boundary?.ring?.length);

  const onCancel = () => {
    clearScopeDraw();
    setTool("select");
  };

  const onConfirm = async (preview: SlabBoundary) => {
    try {
      const data = await commitScopeBoundary(sessionId, preview.ring, {
        source: preview.source,
        cad_ref: preview.cad_ref,
        auto_layer: preview.auto_layer,
      });
      setScene(data.scene);
      setActions(data.actions);
      clearScopeDraw();
      setTool("select");
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Could not save slab boundary");
    }
  };

  const onApply = async () => {
    if (!hasSavedBoundary) {
      setEngineError("Confirm the slab boundary before applying");
      return;
    }
    if (!cadAvailable) {
      setEngineError("CAD source unavailable — apply boundary requires CAD geometry");
      return;
    }
    if (needsApplyBoundaryConfirm(counts, scene?.polygons) && !confirmApplyBoundary()) {
      return;
    }
    try {
      const data = await applyScopeBoundary(sessionId);
      setScene(data.scene);
      setCounts(data.counts);
      setActions(data.actions);
      clearScopeDraw();
      setTool("select");
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Apply boundary failed");
    }
  };

  const onRedetect = async () => {
    try {
      const preview = await autoDetectScopeBoundary(sessionId);
      setBoundaryPreview(preview);
      setBoundaryEditRing(null);
      setTool("select");
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Auto detect failed");
    }
  };

  const onEditPreview = () => {
    if (!boundaryPreview?.ring?.length) return;
    setBoundaryEditRing(boundaryPreview.ring.map((p) => [...p] as [number, number]));
    setTool("scope-edit");
  };

  const onEditSaved = () => {
    const ring = scene?.scope_boundary?.ring;
    if (!ring?.length) return;
    setBoundaryEditRing(ring.map((p) => [...p] as [number, number]));
    setBoundaryPreview(scene!.scope_boundary!);
    setTool("scope-edit");
  };

  const onFinishEdit = async () => {
    if (!boundaryEditRing || boundaryEditRing.length < 3) {
      setEngineError("Boundary needs at least 3 vertices");
      return;
    }
    try {
      const data = await commitScopeBoundary(sessionId, boundaryEditRing, {
        source: boundaryPreview?.source ?? scene?.scope_boundary?.source ?? "drawn",
        cad_ref: boundaryPreview?.cad_ref ?? scene?.scope_boundary?.cad_ref,
        auto_layer: boundaryPreview?.auto_layer ?? scene?.scope_boundary?.auto_layer,
      });
      setScene(data.scene);
      setActions(data.actions);
      clearScopeDraw();
      setTool("select");
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Could not update boundary");
    }
  };

  if (tool === "scope-edit" && boundaryEditRing) {
    const area = ringAreaM2(boundaryEditRing, unitScaleM);
    const perim = ringPerimeter(boundaryEditRing, unitScaleM);
    return (
      <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
        Edit boundary — drag vertices · click edge to insert · Delete removes vertex —{" "}
        {area.toFixed(1)} m² · {perim.toFixed(1)} m —{" "}
        <button type="button" className="underline" onClick={() => void onFinishEdit()}>
          Accept
        </button>
        {" · "}
        <button type="button" className="underline" onClick={onCancel}>
          Cancel
        </button>
      </div>
    );
  }

  if (boundaryPreview) {
    const sourceLabel =
      boundaryPreview.source === "cad_pick"
        ? "CAD pick"
        : boundaryPreview.source === "auto_layer"
          ? `Auto (${boundaryPreview.auto_layer ?? "layer"})`
          : "Drawn";
    return (
      <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
        Boundary preview ({sourceLabel}) — {formatMetrics(boundaryPreview)} —{" "}
        <button type="button" className="underline" onClick={() => void onConfirm(boundaryPreview)}>
          Accept
        </button>
        {" · "}
        <button type="button" className="underline" onClick={onCancel}>
          Cancel
        </button>
        {" · "}
        <button type="button" className="underline" onClick={onEditPreview}>
          Edit
        </button>
        {boundaryPreview.source === "auto_layer" ? (
          <>
            {" · "}
            <button type="button" className="underline" onClick={() => void onRedetect()}>
              Redetect
            </button>
          </>
        ) : null}
        {hasSavedBoundary ? (
          <>
            {" · "}
            <button type="button" className="underline" onClick={() => void onApply()}>
              Apply Boundary
            </button>
          </>
        ) : null}
      </div>
    );
  }

  if (tool === "scope-pick") {
    return (
      <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
        Pick Boundary — click a closed CAD polyline —{" "}
        <button type="button" className="underline" onClick={onCancel}>
          Esc to cancel
        </button>
      </div>
    );
  }

  if (tool === "scope-auto") {
    return (
      <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
        Auto Detect Boundary — detecting slab outline… —{" "}
        <button type="button" className="underline" onClick={onCancel}>
          Cancel
        </button>
      </div>
    );
  }

  if (tool === "scope-draw" && polylineDraw) {
    const live = liveDrawRing(polylineDraw);
    const area =
      live.length >= 3 ? ringAreaM2(live, unitScaleM) : 0;
    const perim =
      live.length >= 2 ? ringPerimeter(live, unitScaleM) : 0;
    const metrics =
      live.length >= 2
        ? ` — ${area > 0 ? `${area.toFixed(1)} m²` : "…"} · ${perim.toFixed(1)} m`
        : "";
    return (
      <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
        Draw Boundary (manual) — click vertices · click first point to close · Enter to finish
        {metrics} —{" "}
        <button type="button" className="underline" onClick={onCancel}>
          Esc to cancel
        </button>
      </div>
    );
  }

  if (hasSavedBoundary && tool === "select") {
    return (
      <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
        Slab boundary saved — {formatMetrics(scene!.scope_boundary!)} —{" "}
        <button type="button" className="underline" onClick={() => void onApply()}>
          Apply Boundary
        </button>
        {" · "}
        <button type="button" className="underline" onClick={onEditSaved}>
          Edit vertices
        </button>
        {" · "}
        <button
          type="button"
          className="underline"
          onClick={async () => {
            try {
              const data = await clearScopeBoundary(sessionId);
              setScene(data.scene);
              setActions(data.actions);
              clearScopeDraw();
            } catch (e) {
              setEngineError(e instanceof Error ? e.message : "Could not clear boundary");
            }
          }}
        >
          Clear
        </button>
      </div>
    );
  }

  return null;
}
