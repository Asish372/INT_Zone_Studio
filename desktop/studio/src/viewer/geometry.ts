import type { Bounds, PolygonIdMode, PolygonRecord, SceneData } from "../types";

export function computeBounds(scene: SceneData): Bounds {
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity;

  const consider = (x: number, y: number) => {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  };

  for (const line of scene.cad_lines ?? []) {
    consider(line[0], line[1]);
    consider(line[2], line[3]);
  }
  for (const poly of scene.polygons ?? []) {
    for (const [x, y] of poly.ring ?? []) consider(x, y);
  }

  if (!isFinite(minX)) return { minX: 0, minY: 0, maxX: 1000, maxY: 1000 };

  let bw = maxX - minX;
  let bh = maxY - minY;
  if (bw <= 0 || bh <= 0) {
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const half = 500;
    return {
      minX: cx - half,
      minY: cy - half,
      maxX: cx + half,
      maxY: cy + half,
    };
  }

  const padX = bw * 0.02 || 1;
  const padY = bh * 0.02 || 1;
  return {
    minX: minX - padX,
    minY: minY - padY,
    maxX: maxX + padX,
    maxY: maxY + padY,
  };
}

export function boundsFromBbox(bbox: [number, number, number, number]): Bounds {
  const [minX, minY, maxX, maxY] = bbox;
  const bw = maxX - minX || 1;
  const bh = maxY - minY || 1;
  const padX = bw * 0.15;
  const padY = bh * 0.15;
  return {
    minX: minX - padX,
    minY: minY - padY,
    maxX: maxX + padX,
    maxY: maxY + padY,
  };
}

export function shoelaceArea(ring: [number, number][]): number {
  let a = 0;
  for (let i = 0; i < ring.length; i++) {
    const j = (i + 1) % ring.length;
    a += ring[i][0] * ring[j][1] - ring[j][0] * ring[i][1];
  }
  return Math.abs(a / 2);
}

export function pointInRing(
  x: number,
  y: number,
  ring: [number, number][],
): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0],
      yi = ring[i][1];
    const xj = ring[j][0],
      yj = ring[j][1];
    if (
      (yi > y) !== (yj > y) &&
      x < ((xj - xi) * (y - yi)) / (yj - yi) + xi
    ) {
      inside = !inside;
    }
  }
  return inside;
}

export function findPolygonAt(
  wx: number,
  wy: number,
  polygons: PolygonRecord[],
): PolygonRecord | null {
  let best: PolygonRecord | null = null;
  let bestArea = Infinity;
  for (const poly of polygons) {
    if (poly.status === "deleted") continue;
    const ring = poly.ring;
    if (!ring || ring.length < 3) continue;
    if (!pointInRing(wx, wy, ring)) continue;
    const area = shoelaceArea(ring);
    if (area < bestArea) {
      bestArea = area;
      best = poly;
    }
  }
  return best;
}

export function findPolygonsInRect(
  minX: number,
  minY: number,
  maxX: number,
  maxY: number,
  polygons: PolygonRecord[],
): PolygonRecord[] {
  const loX = Math.min(minX, maxX);
  const hiX = Math.max(minX, maxX);
  const loY = Math.min(minY, maxY);
  const hiY = Math.max(minY, maxY);
  const hits: PolygonRecord[] = [];
  for (const poly of polygons) {
    if (poly.status === "deleted") continue;
    const ring = poly.ring;
    if (!ring?.length) continue;
    const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
    const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
    if (cx >= loX && cx <= hiX && cy >= loY && cy <= hiY) hits.push(poly);
  }
  return hits;
}

export function polygonCentroid(ring: [number, number][]): [number, number] {
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  return [cx, cy];
}

export function polygonScreenBBox(
  ring: [number, number][],
  scale: number,
): { width: number; height: number } {
  const xs = ring.map((p) => p[0]);
  const ys = ring.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    width: (maxX - minX) * scale,
    height: (maxY - minY) * scale,
  };
}

export function computeAreaThreshold(polygons: PolygonRecord[]): number {
  const areas = polygons
    .filter((p) => p.status !== "deleted")
    .map((p) => p.area_m2 ?? 0)
    .sort((a, b) => b - a);
  if (areas.length === 0) return 0;
  return areas[Math.floor(areas.length * 0.2)] ?? 0;
}

export function computeFitScale(
  bounds: Bounds,
  viewportW: number,
  viewportH: number,
): number {
  const bw = bounds.maxX - bounds.minX || 1;
  const bh = bounds.maxY - bounds.minY || 1;
  return Math.min(viewportW / bw, viewportH / bh) * 0.92;
}

export type ZoomTier = "low" | "medium" | "high";

export function computeZoomTier(scale: number, fitScale: number): ZoomTier {
  const ratio = scale / (fitScale || 1);
  if (ratio < 0.45) return "low";
  if (ratio < 1.8) return "medium";
  return "high";
}

function polygonIntersectsViewport(
  ring: [number, number][],
  vp: Bounds,
): boolean {
  for (const [x, y] of ring) {
    if (x >= vp.minX && x <= vp.maxX && y >= vp.minY && y <= vp.maxY) return true;
  }
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  return cx >= vp.minX && cx <= vp.maxX && cy >= vp.minY && cy <= vp.maxY;
}

function screenPointInsidePolygon(
  sx: number,
  sy: number,
  ring: [number, number][],
  worldToScreen: (x: number, y: number) => [number, number],
): boolean {
  const screenRing = ring.map(([x, y]) => worldToScreen(x, y));
  return pointInRing(sx, sy, screenRing);
}

export interface LabelPlacement {
  id: number;
  sx: number;
  sy: number;
  fontSize: number;
  isSelected: boolean;
}

const MIN_LABEL_BBOX_PX = 28;
const LABEL_MIN_DIST_PX = 16;
const LABEL_MAX_NUDGE_PX = 8;

function shouldShowPolygonId(
  poly: PolygonRecord,
  mode: PolygonIdMode,
  isSelected: boolean,
  zoomTier: ZoomTier,
  areaThreshold: number,
  viewportBounds: Bounds,
): boolean {
  if (isSelected) return true;
  if (mode === "off") return false;
  if (mode === "selected") return false;
  if (mode === "all") return true;
  if (zoomTier === "low") return false;
  const ring = poly.ring ?? [];
  if (ring.length < 3) return false;
  if (zoomTier === "medium") return (poly.area_m2 ?? 0) >= areaThreshold;
  return polygonIntersectsViewport(ring, viewportBounds);
}

/** Place polygon ID labels at centroids with adaptive density and clean placement. */
export function layoutPolygonLabels(
  polygons: PolygonRecord[],
  worldToScreen: (x: number, y: number) => [number, number],
  scale: number,
  fitScale: number,
  selectedId: number | null,
  selectedIds: number[],
  viewportW: number,
  viewportH: number,
  mode: PolygonIdMode,
  viewportBounds: Bounds,
  labelsLayerVisible: boolean,
): LabelPlacement[] {
  const effectiveMode: PolygonIdMode = labelsLayerVisible ? mode : "off";
  const zoomTier = computeZoomTier(scale, fitScale);
  const areaThreshold = computeAreaThreshold(polygons);
  const selectedSet = new Set<number>(selectedIds);
  if (selectedId != null) selectedSet.add(selectedId);

  const placed: LabelPlacement[] = [];
  const occupied: { x: number; y: number; r: number }[] = [];

  const sorted = [...polygons]
    .filter((p) => p.status !== "deleted")
    .sort((a, b) => {
      const aSel = selectedSet.has(a.id) ? 1 : 0;
      const bSel = selectedSet.has(b.id) ? 1 : 0;
      if (aSel !== bSel) return bSel - aSel;
      return (b.area_m2 ?? 0) - (a.area_m2 ?? 0);
    });

  for (const poly of sorted) {
    const ring = poly.ring ?? [];
    if (ring.length < 3) continue;

    const isSelected = selectedSet.has(poly.id);
    if (
      !shouldShowPolygonId(
        poly,
        effectiveMode,
        isSelected,
        zoomTier,
        areaThreshold,
        viewportBounds,
      )
    ) {
      continue;
    }

    const [cx, cy] = polygonCentroid(ring);
    if (!pointInRing(cx, cy, ring)) continue;

    const [baseX, baseY] = worldToScreen(cx, cy);
    if (
      baseX < -20 ||
      baseY < -20 ||
      baseX > viewportW + 20 ||
      baseY > viewportH + 20
    ) {
      continue;
    }

    const bbox = polygonScreenBBox(ring, scale);
    if (
      !isSelected &&
      (bbox.width < MIN_LABEL_BBOX_PX || bbox.height < MIN_LABEL_BBOX_PX)
    ) {
      continue;
    }

    const fontSize = isSelected
      ? Math.max(9, Math.min(12, Math.sqrt(bbox.width * bbox.height) * 0.18))
      : Math.max(8, Math.min(10, Math.sqrt(bbox.width * bbox.height) * 0.14));

    if (
      !screenPointInsidePolygon(baseX, baseY, ring, worldToScreen)
    ) {
      continue;
    }

    let sx = baseX;
    let sy = baseY;
    let placedCleanly = true;

    const minDist = isSelected ? LABEL_MIN_DIST_PX * 0.75 : LABEL_MIN_DIST_PX;
    const clashAt = (x: number, y: number) =>
      occupied.some((o) => Math.hypot(o.x - x, o.y - y) < minDist + o.r);

    if (clashAt(sx, sy)) {
      placedCleanly = false;
      const nudgeAngles = [0, 1.05, 2.1, 3.15, 4.2, 5.25];
      for (const angle of nudgeAngles) {
        const nx = baseX + Math.cos(angle) * LABEL_MAX_NUDGE_PX;
        const ny = baseY + Math.sin(angle) * LABEL_MAX_NUDGE_PX;
        if (
          screenPointInsidePolygon(nx, ny, ring, worldToScreen) &&
          !clashAt(nx, ny)
        ) {
          sx = nx;
          sy = ny;
          placedCleanly = true;
          break;
        }
      }
    }

    if (!placedCleanly && !isSelected) continue;

    occupied.push({ x: sx, y: sy, r: fontSize * 0.45 });
    placed.push({ id: poly.id, sx, sy, fontSize, isSelected });
  }

  return placed;
}

export function filterPolygons(
  polygons: PolygonRecord[],
  filter: string,
  search: string,
): PolygonRecord[] {
  let list = [...polygons];
  if (filter === "auto") list = list.filter((p) => p.source === "auto" && p.status !== "deleted");
  else if (filter === "recovered") list = list.filter((p) => p.source === "seed" && p.status !== "deleted");
  else if (filter === "deleted") list = list.filter((p) => p.status === "deleted");
  else if (filter === "large") list = list.filter((p) => p.status !== "deleted" && (p.area_m2 ?? 0) > 100);
  else if (filter === "small") list = list.filter((p) => p.status !== "deleted" && (p.area_m2 ?? 0) < 5);
  else if (filter === "approved") list = list.filter((p) => p.review_status === "approved");
  else if (filter === "pending") list = list.filter((p) => (p.review_status ?? "pending") === "pending");
  else if (filter === "rejected") list = list.filter((p) => p.review_status === "rejected");
  else list = list.filter((p) => p.status !== "deleted");

  if (search.trim()) {
    const q = search.trim().toLowerCase();
    list = list.filter((p) => {
      if (String(p.id).includes(q)) return true;
      if ((p.int_zone ?? "").toLowerCase().includes(q)) return true;
      if ((p.area_m2 ?? 0).toFixed(2).includes(q)) return true;
      return false;
    });
  }
  return list;
}
