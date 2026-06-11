/** Snap helpers for slab boundary draw / edit (CAD-like precision). */

import type { CadBoundaryCandidate } from "../types";
import type { PolylineVertex } from "./polylineDraw";

export interface SnapResult {
  point: PolylineVertex;
  kind: "endpoint" | "intersection" | "boundary_vertex" | null;
}

export interface SnapContext {
  raw: PolylineVertex;
  scale: number;
  cadLines: [number, number, number, number][];
  boundaryVertices: PolylineVertex[];
  drawVertices: PolylineVertex[];
}

const SNAP_PX = 10;

function snapToleranceWorld(scale: number): number {
  return SNAP_PX / Math.max(scale, 1e-9);
}

function dist2(a: PolylineVertex, b: PolylineVertex): number {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  return dx * dx + dy * dy;
}

function segmentIntersection(
  a1: PolylineVertex,
  a2: PolylineVertex,
  b1: PolylineVertex,
  b2: PolylineVertex,
): PolylineVertex | null {
  const x1 = a1[0];
  const y1 = a1[1];
  const x2 = a2[0];
  const y2 = a2[1];
  const x3 = b1[0];
  const y3 = b1[1];
  const x4 = b2[0];
  const y4 = b2[1];
  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  if (Math.abs(denom) < 1e-12) return null;
  const px =
    ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom;
  const py =
    ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom;
  const onSeg = (x: number, y: number, sx1: number, sy1: number, sx2: number, sy2: number) => {
    const minX = Math.min(sx1, sx2) - 1e-6;
    const maxX = Math.max(sx1, sx2) + 1e-6;
    const minY = Math.min(sy1, sy2) - 1e-6;
    const maxY = Math.max(sy1, sy2) + 1e-6;
    return x >= minX && x <= maxX && y >= minY && y <= maxY;
  };
  if (
    !onSeg(px, py, x1, y1, x2, y2) ||
    !onSeg(px, py, x3, y3, x4, y4)
  ) {
    return null;
  }
  return [px, py];
}

function collectEndpoints(
  cadLines: [number, number, number, number][],
): PolylineVertex[] {
  const pts: PolylineVertex[] = [];
  for (const [x1, y1, x2, y2] of cadLines) {
    pts.push([x1, y1], [x2, y2]);
  }
  return pts;
}

function nearestPoint(
  raw: PolylineVertex,
  candidates: PolylineVertex[],
  tol2: number,
): { point: PolylineVertex; kind: SnapResult["kind"] } | null {
  let best: PolylineVertex | null = null;
  let bestD = tol2;
  for (const c of candidates) {
    const d = dist2(raw, c);
    if (d <= bestD) {
      bestD = d;
      best = c;
    }
  }
  if (!best) return null;
  return { point: best, kind: "endpoint" };
}

export function snapBoundaryPoint(ctx: SnapContext): SnapResult {
  const tol = snapToleranceWorld(ctx.scale);
  const tol2 = tol * tol;
  const endpoints = [
    ...collectEndpoints(ctx.cadLines),
    ...ctx.boundaryVertices,
    ...ctx.drawVertices,
  ];

  const ep = nearestPoint(ctx.raw, endpoints, tol2);
  if (ep) {
    return {
      point: ep.point,
      kind: ep.kind === "endpoint" && ctx.boundaryVertices.some((v) => dist2(v, ep.point) < 1e-6)
        ? "boundary_vertex"
        : "endpoint",
    };
  }

  const segments: [PolylineVertex, PolylineVertex][] = [];
  for (const [x1, y1, x2, y2] of ctx.cadLines) {
    segments.push([[x1, y1], [x2, y2]]);
  }
  let bestIx: PolylineVertex | null = null;
  let bestIxD = tol2;
  for (let i = 0; i < segments.length; i++) {
    for (let j = i + 1; j < segments.length; j++) {
      const hit = segmentIntersection(
        segments[i][0],
        segments[i][1],
        segments[j][0],
        segments[j][1],
      );
      if (!hit) continue;
      const d = dist2(ctx.raw, hit);
      if (d <= bestIxD) {
        bestIxD = d;
        bestIx = hit;
      }
    }
  }
  if (bestIx) {
    return { point: bestIx, kind: "intersection" };
  }

  return { point: ctx.raw, kind: null };
}

export function findPickCandidateAt(
  x: number,
  y: number,
  candidates: CadBoundaryCandidate[],
): CadBoundaryCandidate | null {
  const pt: PolylineVertex = [x, y];
  let containing: CadBoundaryCandidate[] = [];
  for (const c of candidates) {
    if (pointInRing(x, y, c.ring)) containing.push(c);
  }
  if (containing.length) {
    return containing.reduce((a, b) => (a.area_m2 < b.area_m2 ? a : b));
  }
  let nearest: CadBoundaryCandidate | null = null;
  let best = Infinity;
  for (const c of candidates) {
    const d = ringBoundaryDistance(pt, c.ring);
    if (d < best) {
      best = d;
      nearest = c;
    }
  }
  return nearest;
}

function pointInRing(x: number, y: number, ring: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

function ringBoundaryDistance(pt: PolylineVertex, ring: [number, number][]): number {
  let best = Infinity;
  for (let i = 0; i < ring.length; i++) {
    const j = (i + 1) % ring.length;
    const d = pointSegmentDistance(pt, ring[i], ring[j]);
    if (d < best) best = d;
  }
  return best;
}

function pointSegmentDistance(
  p: PolylineVertex,
  a: PolylineVertex,
  b: PolylineVertex,
): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  if (dx === 0 && dy === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  const t = Math.max(
    0,
    Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)),
  );
  const px = a[0] + t * dx;
  const py = a[1] + t * dy;
  return Math.hypot(p[0] - px, p[1] - py);
}

export function hitTestBoundaryVertex(
  wx: number,
  wy: number,
  ring: PolylineVertex[],
  scale: number,
): number | null {
  const tol2 = snapToleranceWorld(scale) ** 2;
  for (let i = 0; i < ring.length; i++) {
    if (dist2([wx, wy], ring[i]) <= tol2) return i;
  }
  return null;
}

export function hitTestBoundaryEdge(
  wx: number,
  wy: number,
  ring: PolylineVertex[],
  scale: number,
): number | null {
  const tol = snapToleranceWorld(scale);
  let bestEdge: number | null = null;
  let bestD = tol;
  for (let i = 0; i < ring.length; i++) {
    const j = (i + 1) % ring.length;
    const d = pointSegmentDistance([wx, wy], ring[i], ring[j]);
    if (d < bestD) {
      bestD = d;
      bestEdge = j;
    }
  }
  return bestEdge;
}
