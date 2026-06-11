/** Reusable canvas polyline drawing state (slab boundary, manual polygons). */

export type PolylineVertex = [number, number];

export interface PolylineDrawState {
  vertices: PolylineVertex[];
  cursor: PolylineVertex | null;
}

export function createPolylineDraw(): PolylineDrawState {
  return { vertices: [], cursor: null };
}

export function addPolylineVertex(
  state: PolylineDrawState,
  point: PolylineVertex,
): PolylineDrawState {
  return {
    ...state,
    vertices: [...state.vertices, point],
    cursor: point,
  };
}

export function setPolylineCursor(
  state: PolylineDrawState,
  point: PolylineVertex | null,
): PolylineDrawState {
  return { ...state, cursor: point };
}

export function closePolylineRing(
  state: PolylineDrawState,
  minVertices = 3,
): PolylineVertex[] | null {
  if (state.vertices.length < minVertices) return null;
  return [...state.vertices];
}

export function isNearFirstVertex(
  state: PolylineDrawState,
  point: PolylineVertex,
  toleranceWorld: number,
): boolean {
  if (state.vertices.length < minVerticesForClose()) return false;
  const [fx, fy] = state.vertices[0];
  const dx = point[0] - fx;
  const dy = point[1] - fy;
  return dx * dx + dy * dy <= toleranceWorld * toleranceWorld;
}

export function minVerticesForClose(): number {
  return 3;
}

/** World-space snap tolerance scaled from ~8 screen pixels. */
export function polylineCloseToleranceWorld(scale: number): number {
  const px = 8;
  return px / Math.max(scale, 1e-9);
}

export function ringPerimeter(ring: PolylineVertex[], unitScaleM = 0.001): number {
  if (ring.length < 2) return 0;
  let len = 0;
  for (let i = 0; i < ring.length; i++) {
    const j = (i + 1) % ring.length;
    len += Math.hypot(ring[j][0] - ring[i][0], ring[j][1] - ring[i][1]);
  }
  return len * unitScaleM;
}

export function ringAreaM2(ring: PolylineVertex[], unitScaleM = 0.001): number {
  if (ring.length < 3) return 0;
  let a = 0;
  for (let i = 0; i < ring.length; i++) {
    const j = (i + 1) % ring.length;
    a += ring[i][0] * ring[j][1] - ring[j][0] * ring[i][1];
  }
  const native = Math.abs(a / 2);
  return native * unitScaleM * unitScaleM;
}

/** Live draw ring including cursor as closing preview vertex. */
export function liveDrawRing(state: PolylineDrawState): PolylineVertex[] {
  if (!state.vertices.length) return [];
  if (state.cursor) return [...state.vertices, state.cursor];
  return state.vertices;
}
