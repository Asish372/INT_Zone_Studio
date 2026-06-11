import { useEffect, useRef } from "react";
import type { Bounds, SceneData } from "../../types";
import { CANVAS_COLORS } from "../../viewer/canvasColors";
import { isActiveWorkspacePolygon } from "../../viewer/geometry";

interface Camera {
  scale: number;
  offsetX: number;
  offsetY: number;
}

interface MinimapProps {
  scene: SceneData;
  bounds: Bounds;
  camera: Camera;
  viewportSize: { w: number; h: number };
  onNavigate: (mx: number, my: number) => void;
}

export function Minimap({
  scene,
  bounds,
  camera,
  viewportSize,
  onNavigate,
}: MinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const mw = canvas.width;
    const mh = canvas.height;
    ctx.fillStyle = CANVAS_COLORS.minimapBg;
    ctx.fillRect(0, 0, mw, mh);

    const bw = bounds.maxX - bounds.minX;
    const bh = bounds.maxY - bounds.minY;
    const ms = Math.min(mw / bw, mh / bh) * 0.9;
    const mx = (mw - bw * ms) / 2 - bounds.minX * ms;
    const my = (mh + bh * ms) / 2 + bounds.minY * ms;

    ctx.strokeStyle = CANVAS_COLORS.minimapCad;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (const [x1, y1, x2, y2] of (scene.cad_lines ?? []).slice(0, 12000)) {
      ctx.moveTo(x1 * ms + mx, -y1 * ms + my);
      ctx.lineTo(x2 * ms + mx, -y2 * ms + my);
    }
    ctx.stroke();

    ctx.strokeStyle = CANVAS_COLORS.polygonAuto;
    ctx.lineWidth = 0.6;
    for (const poly of scene.polygons ?? []) {
      if (!isActiveWorkspacePolygon(poly)) continue;
      const ring = poly.ring ?? [];
      if (ring.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(ring[0][0] * ms + mx, -ring[0][1] * ms + my);
      for (let i = 1; i < ring.length; i++) {
        ctx.lineTo(ring[i][0] * ms + mx, -ring[i][1] * ms + my);
      }
      ctx.closePath();
      ctx.stroke();
    }

    const screenToWorld = (sx: number, sy: number): [number, number] => [
      (sx - camera.offsetX) / camera.scale,
      -(sy - camera.offsetY) / camera.scale,
    ];

    const [wx0, wy0] = screenToWorld(0, 0);
    const [wx1, wy1] = screenToWorld(viewportSize.w, viewportSize.h);
    const vx0 = Math.min(wx0, wx1) * ms + mx;
    const vx1 = Math.max(wx0, wx1) * ms + mx;
    const vy0 = -Math.max(wy0, wy1) * ms + my;
    const vy1 = -Math.min(wy0, wy1) * ms + my;
    ctx.strokeStyle = CANVAS_COLORS.brandPrimary;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(vx0, vy0, vx1 - vx0, vy1 - vy0);
  }, [scene, bounds, camera, viewportSize]);

  return (
    <div className="minimap-panel">
      <div className="minimap-title">Navigation</div>
      <canvas
        ref={canvasRef}
        width={160}
        height={120}
        className="minimap-canvas"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          onNavigate(e.clientX - rect.left, e.clientY - rect.top);
        }}
      />
    </div>
  );
}
