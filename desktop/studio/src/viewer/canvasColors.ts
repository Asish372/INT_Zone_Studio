/** Canvas 2D cannot use CSS variables — CAD workspace palette. */
export const CANVAS_COLORS = {
  viewportBg: "#1a1a1e",
  grid: "rgba(255, 255, 255, 0.06)",
  cadLine: "rgba(255, 255, 255, 0.82)",
  polygonAuto: "#06b6d4",
  polygonAutoFill: "rgba(6, 182, 212, 0.035)",
  polygonSeed: "#22c55e",
  polygonSelected: "#facc15",
  polygonSelectedFill: "rgba(250, 204, 21, 0.08)",
  polygonDeleted: "#ef4444",
  labelDefault: "rgba(232, 232, 236, 0.72)",
  labelSelected: "#1a1a1e",
  labelHalo: "rgba(0, 0, 0, 0.45)",
  brandPrimary: "#3b82f6",
  minimapBg: "#141418",
  minimapCad: "rgba(220, 220, 230, 0.5)",
  minimapPoly: "rgba(6, 182, 212, 0.55)",
} as const;
