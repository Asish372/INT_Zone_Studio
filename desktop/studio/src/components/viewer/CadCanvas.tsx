import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Plus, Minus, Maximize2 } from "lucide-react";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { Bounds, LayerVisibility, PolygonIdMode, SceneData, SeedPreview } from "../../types";
import {
  boundsFromBbox,
  computeBounds,
  computeFitScale,
  findPolygonAt,
  findPolygonsInRect,
  layoutPolygonLabels,
} from "../../viewer/geometry";
import type { SuspectedGapRegion } from "../../types";
import { CANVAS_COLORS } from "../../viewer/canvasColors";
import {
  confirmRecover,
  deletePolygon,
  previewRecover,
  selectPolygon,
  selectPolygons,
} from "../../api/engine";
import { Minimap } from "./Minimap";

interface Camera {
  scale: number;
  offsetX: number;
  offsetY: number;
}

const MIN_ZOOM_SCALE = 0.002;
const MAX_ZOOM_SCALE = 800;
const WHEEL_ZOOM_INTENSITY = 0.0012;

function worldToScreen(x: number, y: number, cam: Camera): [number, number] {
  return [x * cam.scale + cam.offsetX, -y * cam.scale + cam.offsetY];
}

function screenToWorld(sx: number, sy: number, cam: Camera): [number, number] {
  return [(sx - cam.offsetX) / cam.scale, -(sy - cam.offsetY) / cam.scale];
}

function zoomToPolygon(
  ring: [number, number][],
  cam: Camera,
  w: number,
  h: number,
) {
  const xs = ring.map((p) => p[0]);
  const ys = ring.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const bw = maxX - minX || 1;
  const bh = maxY - minY || 1;
  cam.scale = Math.min(w / bw, h / bh) * 0.55;
  cam.offsetX = (w - bw * cam.scale) / 2 - minX * cam.scale;
  cam.offsetY = (h + bh * cam.scale) / 2 + minY * cam.scale;
}

function drawPolygonLabel(
  ctx: CanvasRenderingContext2D,
  tx: number,
  ty: number,
  label: string,
  fontSize: number,
  isSelected: boolean,
) {
  ctx.font = `bold ${fontSize}px "Segoe UI", sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  if (isSelected) {
    const r = Math.max(fontSize * 0.75, 11);
    ctx.beginPath();
    ctx.arc(tx, ty, r, 0, Math.PI * 2);
    ctx.fillStyle = CANVAS_COLORS.polygonSelected;
    ctx.fill();
    ctx.fillStyle = CANVAS_COLORS.labelSelected;
    ctx.fillText(label, tx, ty);
    return;
  }

  ctx.strokeStyle = CANVAS_COLORS.labelHalo;
  ctx.lineWidth = 2;
  ctx.strokeText(label, tx, ty);
  ctx.fillStyle = CANVAS_COLORS.labelDefault;
  ctx.fillText(label, tx, ty);
}

function getViewportWorldBounds(w: number, h: number, cam: Camera) {
  const [x0, y0] = screenToWorld(0, 0, cam);
  const [x1, y1] = screenToWorld(w, h, cam);
  return {
    minX: Math.min(x0, x1),
    maxX: Math.max(x0, x1),
    minY: Math.min(y0, y1),
    maxY: Math.max(y0, y1),
  };
}

function segmentInView(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  vp: ReturnType<typeof getViewportWorldBounds>,
): boolean {
  const minX = Math.min(x1, x2);
  const maxX = Math.max(x1, x2);
  const minY = Math.min(y1, y2);
  const maxY = Math.max(y1, y2);
  return !(maxX < vp.minX || minX > vp.maxX || maxY < vp.minY || minY > vp.maxY);
}

function polyInView(
  ring: [number, number][],
  vp: ReturnType<typeof getViewportWorldBounds>,
): boolean {
  for (const [x, y] of ring) {
    if (x >= vp.minX && x <= vp.maxX && y >= vp.minY && y <= vp.maxY) return true;
  }
  return false;
}

function drawPreviewRing(
  ctx: CanvasRenderingContext2D,
  preview: SeedPreview,
  cam: Camera,
) {
  const ring = preview.ring;
  if (ring.length < 2) return;
  ctx.fillStyle = "rgba(34, 197, 94, 0.12)";
  ctx.strokeStyle = CANVAS_COLORS.polygonSeed;
  ctx.setLineDash([8, 4]);
  ctx.lineWidth = 2;
  ctx.beginPath();
  const [fx, fy] = worldToScreen(ring[0][0], ring[0][1], cam);
  ctx.moveTo(fx, fy);
  for (let i = 1; i < ring.length; i++) {
    const [sx, sy] = worldToScreen(ring[i][0], ring[i][1], cam);
    ctx.lineTo(sx, sy);
  }
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.setLineDash([]);
}

function paintScene(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  cam: Camera,
  scene: SceneData,
  layers: LayerVisibility,
  selectedId: number | null,
  selectedIds: number[],
  hoverId: number | null,
  seedPreview: SeedPreview | null,
  zoomRect: { x0: number; y0: number; x1: number; y1: number } | null,
  selectRect: { x0: number; y0: number; x1: number; y1: number } | null,
  comparisonOverlay: boolean,
  markups: { x: number; y: number; text: string }[],
  showVertices: boolean,
  suspectedGaps: SuspectedGapRegion[],
  polygonIdMode: PolygonIdMode,
  sceneBounds: Bounds,
) {
  ctx.fillStyle = CANVAS_COLORS.viewportBg;
  ctx.fillRect(0, 0, w, h);

  const step = 50 * cam.scale;
  if (step >= 8) {
    ctx.strokeStyle = CANVAS_COLORS.grid;
    ctx.lineWidth = 1;
    const startX = cam.offsetX % step;
    for (let x = startX; x < w; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    const startY = cam.offsetY % step;
    for (let y = startY; y < h; y += step) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
  }

  const vp = getViewportWorldBounds(w, h, cam);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  if (layers.cad) {
    ctx.strokeStyle = CANVAS_COLORS.cadLine;
    ctx.lineWidth = 0.7;
    ctx.beginPath();
    for (const [x1, y1, x2, y2] of scene.cad_lines ?? []) {
      if (!segmentInView(x1, y1, x2, y2, vp)) continue;
      const [sx1, sy1] = worldToScreen(x1, y1, cam);
      const [sx2, sy2] = worldToScreen(x2, y2, cam);
      ctx.moveTo(sx1, sy1);
      ctx.lineTo(sx2, sy2);
    }
    ctx.stroke();
  }

  for (const poly of scene.polygons ?? []) {
    const ring = poly.ring ?? [];
    if (ring.length < 2) continue;
    const isDeleted = poly.status === "deleted";
    const isSeed = poly.source === "seed";
    if (isDeleted && !layers.deleted) continue;
    if (isSeed && !layers.seed) continue;
    if (!isSeed && !isDeleted && !layers.auto) continue;
    if (!polyInView(ring, vp) && poly.id !== selectedId) continue;

    const isSelected = selectedIds.includes(poly.id) || poly.id === selectedId;
    const isHover = poly.id === hoverId && !isSelected;
    ctx.beginPath();
    const [fx, fy] = worldToScreen(ring[0][0], ring[0][1], cam);
    ctx.moveTo(fx, fy);
    for (let i = 1; i < ring.length; i++) {
      const [sx, sy] = worldToScreen(ring[i][0], ring[i][1], cam);
      ctx.lineTo(sx, sy);
    }
    ctx.closePath();

    if (isDeleted) {
      ctx.fillStyle = "rgba(239, 68, 68, 0.08)";
      ctx.strokeStyle = CANVAS_COLORS.polygonDeleted;
      ctx.setLineDash([5, 4]);
      ctx.lineWidth = 1.2;
    } else if (isSelected) {
      ctx.fillStyle = CANVAS_COLORS.polygonSelectedFill;
      ctx.strokeStyle = CANVAS_COLORS.polygonSelected;
      ctx.setLineDash([]);
      ctx.lineWidth = 2.5;
    } else if (isHover) {
      ctx.fillStyle = "rgba(250, 204, 21, 0.06)";
      ctx.strokeStyle = "#fde047";
      ctx.setLineDash([]);
      ctx.lineWidth = 2;
    } else if (comparisonOverlay && poly.source === "auto") {
      ctx.fillStyle = "rgba(34, 197, 94, 0.05)";
      ctx.strokeStyle = "#22c55e";
      ctx.setLineDash([]);
      ctx.lineWidth = 1.5;
    } else if (isSeed) {
      ctx.fillStyle = "rgba(34, 197, 94, 0.04)";
      ctx.strokeStyle = CANVAS_COLORS.polygonSeed;
      ctx.setLineDash([7, 4]);
      ctx.lineWidth = 1.8;
    } else {
      ctx.fillStyle = CANVAS_COLORS.polygonAutoFill;
      ctx.strokeStyle = CANVAS_COLORS.polygonAuto;
      ctx.setLineDash([]);
      ctx.lineWidth = 1.2;
    }
    ctx.fill();
    ctx.stroke();

    if (showVertices && !isDeleted) {
      ctx.fillStyle = isSelected ? CANVAS_COLORS.polygonSelected : "#94a3b8";
      for (const [vx, vy] of ring) {
        const [sx, sy] = worldToScreen(vx, vy, cam);
        ctx.beginPath();
        ctx.arc(sx, sy, isSelected ? 3.5 : 2.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  ctx.setLineDash([]);

  const fitScale = computeFitScale(sceneBounds, w, h);
  const labels = layoutPolygonLabels(
    scene.polygons ?? [],
    (x, y) => worldToScreen(x, y, cam),
    cam.scale,
    fitScale,
    selectedId,
    selectedIds,
    w,
    h,
    polygonIdMode,
    vp,
    layers.labels,
  );
  for (const label of labels) {
    drawPolygonLabel(
      ctx,
      label.sx,
      label.sy,
      String(label.id),
      label.fontSize,
      label.isSelected,
    );
  }

  if (seedPreview) drawPreviewRing(ctx, seedPreview, cam);

  for (const m of markups) {
    const [sx, sy] = worldToScreen(m.x, m.y, cam);
    ctx.fillStyle = "#f59e0b";
    ctx.beginPath();
    ctx.arc(sx, sy, 4, 0, Math.PI * 2);
    ctx.fill();
    if (m.text) {
      ctx.fillStyle = "#f59e0b";
      ctx.font = "10px sans-serif";
      ctx.fillText(m.text, sx + 6, sy - 6);
    }
  }

  for (const gap of suspectedGaps) {
    const [minX, minY, maxX, maxY] = gap.bbox;
    const [cx, cy] = gap.center;
    const [sx0, sy0] = worldToScreen(minX, maxY, cam);
    const [sx1, sy1] = worldToScreen(maxX, minY, cam);
    ctx.strokeStyle = "rgba(245, 158, 11, 0.85)";
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 1.5;
    ctx.strokeRect(sx0, sy0, sx1 - sx0, sy1 - sy0);
    ctx.setLineDash([]);
    const [scx, scy] = worldToScreen(cx, cy, cam);
    ctx.fillStyle = "rgba(245, 158, 11, 0.9)";
    ctx.beginPath();
    ctx.arc(scx, scy, 5, 0, Math.PI * 2);
    ctx.fill();
  }

  if (selectRect) {
    ctx.strokeStyle = "#0078D4";
    ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1;
    ctx.strokeRect(
      Math.min(selectRect.x0, selectRect.x1),
      Math.min(selectRect.y0, selectRect.y1),
      Math.abs(selectRect.x1 - selectRect.x0),
      Math.abs(selectRect.y1 - selectRect.y0),
    );
    ctx.setLineDash([]);
  }

  if (zoomRect) {
    ctx.strokeStyle = CANVAS_COLORS.brandPrimary;
    ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1;
    ctx.strokeRect(
      Math.min(zoomRect.x0, zoomRect.x1),
      Math.min(zoomRect.y0, zoomRect.y1),
      Math.abs(zoomRect.x1 - zoomRect.x0),
      Math.abs(zoomRect.y1 - zoomRect.y0),
    );
    ctx.setLineDash([]);
  }
}

export function CadCanvas() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const camRef = useRef<Camera>({ scale: 1, offsetX: 0, offsetY: 0 });
  const panningRef = useRef(false);
  const [isPanning, setIsPanning] = useState(false);
  const lastRef = useRef({ x: 0, y: 0 });
  const zoomRectRef = useRef<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const selectRectRef = useRef<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const viewportSizeRef = useRef({ w: 0, h: 0 });
  const camInitializedRef = useRef(false);
  const fittedSourceRef = useRef<string | null>(null);
  const spacePanRef = useRef(false);
  const [spaceHeld, setSpaceHeld] = useState(false);

  const scene = useWorkspaceStore((s) => s.scene);
  const sourceFile = useWorkspaceStore((s) => s.sourceFile);
  const layers = useWorkspaceStore((s) => s.layers);
  const tool = useWorkspaceStore((s) => s.tool);
  const selectedId = useWorkspaceStore((s) => s.selectedId);
  const selectedIds = useWorkspaceStore((s) => s.selectedIds);
  const hoverId = useWorkspaceStore((s) => s.hoverId);
  const comparisonOverlay = useWorkspaceStore((s) => s.comparisonOverlay);
  const markups = useWorkspaceStore((s) => s.markups);
  const seedPreview = useWorkspaceStore((s) => s.seedPreview);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const setCoords = useWorkspaceStore((s) => s.setCoords);
  const setSelected = useWorkspaceStore((s) => s.setSelected);
  const setSelectedIds = useWorkspaceStore((s) => s.setSelectedIds);
  const setHoverId = useWorkspaceStore((s) => s.setHoverId);
  const setSeedPreview = useWorkspaceStore((s) => s.setSeedPreview);
  const setScene = useWorkspaceStore((s) => s.setScene);
  const setCounts = useWorkspaceStore((s) => s.setCounts);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const showVertices = useWorkspaceStore((s) => s.showVertices);
  const polygonIdMode = useWorkspaceStore((s) => s.canvasOverlays.polygonIdMode);
  const showMinimap = useWorkspaceStore((s) => s.panelVisibility.minimap);
  const validation = useWorkspaceStore((s) => s.validation);

  const suspectedGaps = useMemo(
    () => (validation?.suspected_gaps ?? []).filter((g) => g.recoverable),
    [validation],
  );

  const bounds = useMemo(
    () => (scene ? computeBounds(scene) : null),
    [scene],
  );

  const draw = useCallback(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas || !scene || !bounds) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    paintScene(
      ctx,
      wrap.clientWidth,
      wrap.clientHeight,
      camRef.current,
      scene,
      layers,
      selectedId,
      selectedIds,
      hoverId,
      seedPreview,
      zoomRectRef.current,
      selectRectRef.current,
      comparisonOverlay,
      markups,
      showVertices,
      suspectedGaps,
      polygonIdMode,
      bounds,
    );
  }, [
    scene,
    bounds,
    layers,
    selectedId,
    selectedIds,
    hoverId,
    seedPreview,
    comparisonOverlay,
    markups,
    showVertices,
    suspectedGaps,
    polygonIdMode,
  ]);

  const fitToView = useCallback((): boolean => {
    const wrap = wrapRef.current;
    if (!wrap || !scene || !bounds) return false;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    if (w < 10 || h < 10) return false;
    let fitBounds = bounds;
    const bw = bounds.maxX - bounds.minX;
    const bh = bounds.maxY - bounds.minY;
    if (bw <= 0 || bh <= 0) {
      const polys = scene.polygons?.filter((p) => p.status !== "deleted") ?? [];
      if (polys.length > 0) {
        const xs = polys.flatMap((p) => (p.ring ?? []).map((pt) => pt[0]));
        const ys = polys.flatMap((p) => (p.ring ?? []).map((pt) => pt[1]));
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        fitBounds = boundsFromBbox([minX, minY, maxX, maxY]);
      } else {
        return false;
      }
    }
    const fbw = fitBounds.maxX - fitBounds.minX;
    const fbh = fitBounds.maxY - fitBounds.minY;
    if (fbw <= 0 || fbh <= 0) return false;
    camRef.current.scale = Math.min(w / fbw, h / fbh) * 0.92;
    camRef.current.offsetX =
      (w - fbw * camRef.current.scale) / 2 - fitBounds.minX * camRef.current.scale;
    camRef.current.offsetY =
      (h + fbh * camRef.current.scale) / 2 + fitBounds.minY * camRef.current.scale;
    camInitializedRef.current = true;
    fittedSourceRef.current = useWorkspaceStore.getState().sourceFile || "__scene__";
    viewportSizeRef.current = { w, h };
    draw();
    return true;
  }, [scene, bounds, draw]);

  const zoomAt = useCallback(
    (mx: number, my: number, factor: number) => {
      const cam = camRef.current;
      const nextScale = Math.max(
        MIN_ZOOM_SCALE,
        Math.min(MAX_ZOOM_SCALE, cam.scale * factor),
      );
      if (nextScale === cam.scale) return;
      const [wx, wy] = screenToWorld(mx, my, cam);
      cam.scale = nextScale;
      const [sx, sy] = worldToScreen(wx, wy, cam);
      cam.offsetX += mx - sx;
      cam.offsetY += my - sy;
      camInitializedRef.current = true;
      draw();
    },
    [draw],
  );

  useEffect(() => {
    const handler = () => {
      void fitToView();
    };
    window.addEventListener("studio:fit-view", handler);
    return () => window.removeEventListener("studio:fit-view", handler);
  }, [fitToView]);

  // Fit once when a new drawing loads — retries until the panel has real dimensions.
  useEffect(() => {
    if (!scene || !bounds) return;

    const fileKey = sourceFile || "__scene__";
    if (fittedSourceRef.current === fileKey && camInitializedRef.current) return;

    const attempt = () => fitToView();
    if (attempt()) return;

    const timers = [50, 120, 250, 500, 1000].map((ms) =>
      window.setTimeout(attempt, ms),
    );
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [scene, sourceFile, bounds, fitToView]);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ bbox: [number, number, number, number]; center?: [number, number] }>).detail;
      const wrap = wrapRef.current;
      if (!wrap || !detail?.bbox) return;
      const [minX, minY, maxX, maxY] = detail.bbox;
      const bw = maxX - minX || 1;
      const bh = maxY - minY || 1;
      const w = wrap.clientWidth;
      const h = wrap.clientHeight;
      camRef.current.scale = Math.min(w / bw, h / bh) * 0.65;
      camRef.current.offsetX =
        (w - bw * camRef.current.scale) / 2 - minX * camRef.current.scale;
      camRef.current.offsetY =
        (h + bh * camRef.current.scale) / 2 + minY * camRef.current.scale;
      camInitializedRef.current = true;
      draw();
    };
    window.addEventListener("studio:zoom-to-region", handler);
    return () => window.removeEventListener("studio:zoom-to-region", handler);
  }, [draw]);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ id: number }>).detail;
      const wrap = wrapRef.current;
      if (!wrap || !scene || !detail?.id) return;
      const poly = scene.polygons?.find((p) => p.id === detail.id);
      if (!poly?.ring?.length) return;
      zoomToPolygon(poly.ring, camRef.current, wrap.clientWidth, wrap.clientHeight);
      camInitializedRef.current = true;
      draw();
    };
    window.addEventListener("studio:zoom-to-polygon", handler);
    return () => window.removeEventListener("studio:zoom-to-polygon", handler);
  }, [scene, draw]);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ x: number; y: number }>).detail;
      const wrap = wrapRef.current;
      if (!wrap || !detail) return;
      const cam = camRef.current;
      const [sx, sy] = worldToScreen(detail.x, detail.y, cam);
      cam.offsetX += wrap.clientWidth / 2 - sx;
      cam.offsetY += wrap.clientHeight / 2 - sy;
      camInitializedRef.current = true;
      setCoords(detail.x, detail.y);
      draw();
    };
    window.addEventListener("studio:go-to-coordinates", handler);
    return () => window.removeEventListener("studio:go-to-coordinates", handler);
  }, [draw, setCoords]);

  useEffect(() => {
    if (!scene) {
      camInitializedRef.current = false;
      fittedSourceRef.current = null;
      camRef.current = { scale: 1, offsetX: 0, offsetY: 0 };
      viewportSizeRef.current = { w: 0, h: 0 };
    }
  }, [scene]);

  useEffect(() => {
    if (!sourceFile) return;
    if (fittedSourceRef.current && fittedSourceRef.current !== sourceFile) {
      camInitializedRef.current = false;
      fittedSourceRef.current = null;
    }
  }, [sourceFile]);

  useEffect(() => {
    draw();
  }, [draw]);

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = wrap.clientWidth;
      const h = wrap.clientHeight;
      const prev = viewportSizeRef.current;

      if (!camInitializedRef.current && scene && bounds) {
        fitToView();
      } else if (
        camInitializedRef.current &&
        prev.w > 0 &&
        prev.h > 0 &&
        (prev.w !== w || prev.h !== h)
      ) {
        const cam = camRef.current;
        const [wx, wy] = screenToWorld(prev.w / 2, prev.h / 2, cam);
        cam.offsetX = w / 2 - wx * cam.scale;
        cam.offsetY = h / 2 + wy * cam.scale;
      }

      viewportSizeRef.current = { w, h };
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [scene, bounds, draw, fitToView]);

  const handleSelect = async (id: number | null) => {
    try {
      const poly = await selectPolygon(sessionId, id);
      setSelected(id, poly);
      draw();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Select failed");
    }
  };

  const handleSeedClick = async (wx: number, wy: number) => {
    try {
      const preview = await previewRecover(sessionId, wx, wy);
      setSeedPreview(preview, { x: wx, y: wy });
      draw();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Recovery preview failed");
      setActions([
        {
          message: e instanceof Error ? e.message : "Recovery failed",
          kind: "warn",
          at: new Date().toISOString(),
        },
        ...useWorkspaceStore.getState().actions,
      ]);
    }
  };

  const startPan = (mx: number, my: number, e: React.MouseEvent) => {
    panningRef.current = true;
    setIsPanning(true);
    lastRef.current = { x: mx, y: my };
    e.preventDefault();
  };

  const onMouseDown = (e: React.MouseEvent) => {
    if (!scene) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Photoshop-style: Space held = temporary hand (pan only, no select/zoom)
    if (e.button === 1 || (e.button === 0 && (spacePanRef.current || tool === "pan"))) {
      startPan(mx, my, e);
      return;
    }

    const [wx, wy] = screenToWorld(mx, my, camRef.current);

    if (tool === "add" && e.button === 0) {
      void handleSeedClick(wx, wy);
      return;
    }
    if ((tool === "select" || tool === "rect-select") && e.button === 0) {
      if (tool === "rect-select") {
        selectRectRef.current = { x0: mx, y0: my, x1: mx, y1: my };
        draw();
        return;
      }
      const hit = findPolygonAt(wx, wy, scene.polygons ?? []);
      if (e.shiftKey && hit) {
        const next = selectedIds.includes(hit.id)
          ? selectedIds.filter((id) => id !== hit.id)
          : [...selectedIds, hit.id];
        void handleMultiSelect(next);
      } else {
        void handleSelect(hit ? hit.id : null);
      }
      return;
    }
    if (tool === "zoom-window" && e.button === 0) {
      zoomRectRef.current = { x0: mx, y0: my, x1: mx, y1: my };
      draw();
    }
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!scene) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const [wx, wy] = screenToWorld(mx, my, camRef.current);
    setCoords(wx, wy);

    if (!spacePanRef.current && (tool === "select" || tool === "rect-select")) {
      const hit = findPolygonAt(wx, wy, scene.polygons ?? []);
      const newHover = hit?.id ?? null;
      if (newHover !== hoverId) {
        setHoverId(newHover);
      }
    } else if (spacePanRef.current && hoverId !== null) {
      setHoverId(null);
    }

    if (selectRectRef.current && tool === "rect-select") {
      selectRectRef.current.x1 = mx;
      selectRectRef.current.y1 = my;
      draw();
      return;
    }

    if (zoomRectRef.current && tool === "zoom-window") {
      zoomRectRef.current.x1 = mx;
      zoomRectRef.current.y1 = my;
      draw();
      return;
    }

    if (!panningRef.current) return;
    const cam = camRef.current;
    cam.offsetX += mx - lastRef.current.x;
    cam.offsetY += my - lastRef.current.y;
    lastRef.current = { x: mx, y: my };
    draw();
  };

  const handleMultiSelect = async (ids: number[]) => {
    try {
      const data = await selectPolygons(sessionId, ids);
      const first = data.selected[0] ?? null;
      setSelectedIds(data.selected_ids, first);
      draw();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Select failed");
    }
  };

  const onMouseUp = () => {
    if (selectRectRef.current && tool === "rect-select" && scene) {
      const sr = selectRectRef.current;
      const [wx0, wy0] = screenToWorld(sr.x0, sr.y0, camRef.current);
      const [wx1, wy1] = screenToWorld(sr.x1, sr.y1, camRef.current);
      const hits = findPolygonsInRect(wx0, wy0, wx1, wy1, scene.polygons ?? []);
      selectRectRef.current = null;
      void handleMultiSelect(hits.map((p) => p.id));
      return;
    }
    if (zoomRectRef.current && tool === "zoom-window") {
      const zr = zoomRectRef.current;
      const [wx0, wy0] = screenToWorld(zr.x0, zr.y0, camRef.current);
      const [wx1, wy1] = screenToWorld(zr.x1, zr.y1, camRef.current);
      const wrap = wrapRef.current!;
      const minX = Math.min(wx0, wx1);
      const maxX = Math.max(wx0, wx1);
      const minY = Math.min(wy0, wy1);
      const maxY = Math.max(wy0, wy1);
      const bw = maxX - minX || 1;
      const bh = maxY - minY || 1;
      const w = wrap.clientWidth;
      const h = wrap.clientHeight;
      camRef.current.scale = Math.min(w / bw, h / bh) * 0.95;
      camRef.current.offsetX =
        (w - bw * camRef.current.scale) / 2 - minX * camRef.current.scale;
      camRef.current.offsetY =
        (h + bh * camRef.current.scale) / 2 + minY * camRef.current.scale;
      zoomRectRef.current = null;
      draw();
    }
    panningRef.current = false;
    setIsPanning(false);
  };

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;

    const onWheel = (e: WheelEvent) => {
      if (!scene) return;
      e.preventDefault();
      e.stopPropagation();
      const rect = canvas.getBoundingClientRect();
      const factor = Math.exp(-e.deltaY * WHEEL_ZOOM_INTENSITY);
      zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
    };

    wrap.addEventListener("wheel", onWheel, { passive: false });
    return () => wrap.removeEventListener("wheel", onWheel);
  }, [scene, zoomAt]);

  useEffect(() => {
    const isTypingTarget = (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement)) return false;
      return Boolean(
        target.closest("input, textarea, select, [contenteditable='true']"),
      );
    };

    const releaseSpacePan = () => {
      spacePanRef.current = false;
      setSpaceHeld(false);
      if (panningRef.current) {
        panningRef.current = false;
        setIsPanning(false);
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      if (e.code === "Space" && !e.repeat) {
        spacePanRef.current = true;
        setSpaceHeld(true);
        e.preventDefault();
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") releaseSpacePan();
    };
    const onBlur = () => releaseSpacePan();

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onBlur);
    };
  }, []);

  useEffect(() => {
    const onKey = async (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      const st = useWorkspaceStore.getState();
      if (e.key === "Escape" && st.seedPreview) {
        setSeedPreview(null, null);
        draw();
      }
      if (e.key === "Delete" && st.selectedId) {
        try {
          const data = await deletePolygon(st.sessionId, st.selectedId);
          setScene(data.scene);
          setCounts(data.counts);
          setActions(data.actions);
          setSelected(null, null);
          draw();
        } catch (err) {
          setEngineError(err instanceof Error ? err.message : "Delete failed");
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [draw, setActions, setCounts, setEngineError, setScene, setSeedPreview, setSelected]);

  return (
    <div className="viewer-viewport">
      <div
        ref={wrapRef}
        className={`canvas-wrap${spaceHeld ? " canvas-wrap-space-pan" : ""}${isPanning ? " canvas-wrap-panning" : ""}`}
        style={{
          cursor: isPanning
            ? "grabbing"
            : spaceHeld || tool === "pan"
              ? "grab"
              : tool === "add"
                ? "crosshair"
                : tool === "zoom-window" || tool === "rect-select"
                  ? "crosshair"
                  : "default",
        }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        <canvas ref={canvasRef} className="block h-full w-full" />
        {!scene && (
          <div className="canvas-empty">
            <p>Open a DXF or DWG to view detected polygons</p>
          </div>
        )}
        {bounds && scene && showMinimap && (
          <Minimap
            scene={scene}
            bounds={bounds}
            camera={camRef.current}
            viewportSize={{
              w: wrapRef.current?.clientWidth ?? 0,
              h: wrapRef.current?.clientHeight ?? 0,
            }}
            onNavigate={(mx, my) => {
              const cam = camRef.current;
              const wrap = wrapRef.current;
              if (!wrap) return;
              const bw = bounds.maxX - bounds.minX;
              const bh = bounds.maxY - bounds.minY;
              const ms = Math.min(160 / bw, 120 / bh) * 0.9;
              const mmx = (160 - bw * ms) / 2 - bounds.minX * ms;
              const mmy = (120 + bh * ms) / 2 + bounds.minY * ms;
              const wx = (mx - mmx) / ms;
              const wy = -(my - mmy) / ms;
              const [sx, sy] = worldToScreen(wx, wy, cam);
              cam.offsetX += wrap.clientWidth / 2 - sx;
              cam.offsetY += wrap.clientHeight / 2 - sy;
              draw();
            }}
          />
        )}
        <div className="canvas-float-controls">
          <button type="button" className="float-btn" onClick={() => zoomAt((wrapRef.current?.clientWidth ?? 0) / 2, (wrapRef.current?.clientHeight ?? 0) / 2, 1.2)} title="Zoom In">
            <Plus size={16} />
          </button>
          <button type="button" className="float-btn" onClick={() => zoomAt((wrapRef.current?.clientWidth ?? 0) / 2, (wrapRef.current?.clientHeight ?? 0) / 2, 0.82)} title="Zoom Out">
            <Minus size={16} />
          </button>
          <button type="button" className="float-btn" onClick={fitToView} title="Fit View">
            <Maximize2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

export async function confirmSeedRecovery(): Promise<void> {
  const st = useWorkspaceStore.getState();
  if (!st.seedClick || !st.sessionId) return;
  const { x, y } = st.seedClick;
  const data = await confirmRecover(st.sessionId, x, y);
  useWorkspaceStore.getState().setScene(data.scene);
  useWorkspaceStore.getState().setCounts(data.counts);
  useWorkspaceStore.getState().setActions(data.actions);
  useWorkspaceStore.getState().setSelected(data.selected.id, data.selected);
  useWorkspaceStore.getState().setSeedPreview(null, null);
  useWorkspaceStore.getState().setTool("select");
  window.dispatchEvent(new CustomEvent("studio:fit-view"));
}
