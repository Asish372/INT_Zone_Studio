export type PanelLayout = Record<string, number>;

/** Full-width bottom dock vs main work area (VS Code style). */
export const DEFAULT_OUTER_LAYOUT: PanelLayout = {
  main: 72,
  bottom: 28,
};

export const DEFAULT_HORIZONTAL_LAYOUT: PanelLayout = {
  explorer: 11,
  center: 73,
  right: 16,
};

const OUTER_STORAGE_KEY = "int_zone_studio_panels_v";
const HORIZONTAL_STORAGE_KEY = "int_zone_studio_panels_h";
const LEGACY_BOTTOM_STORAGE_KEY = "int_zone_studio_panels_bottom";

function sumLayout(layout: PanelLayout): number {
  return Object.values(layout).reduce((a, b) => a + b, 0);
}

function normalizeLayout(layout: PanelLayout): PanelLayout {
  const total = sumLayout(layout);
  if (total <= 0) return { ...layout };
  const scale = 100 / total;
  const normalized: PanelLayout = {};
  for (const [id, size] of Object.entries(layout)) {
    normalized[id] = Math.round(size * scale * 10) / 10;
  }
  return normalized;
}

export function sanitizeOuterLayout(layout: PanelLayout): PanelLayout {
  if ("table" in layout || "console" in layout || "explorer" in layout || "center" in layout) {
    return { ...DEFAULT_OUTER_LAYOUT };
  }

  const main = layout.main ?? layout.canvas ?? 0;
  const bottom = layout.bottom ?? 0;

  if (main < 45 || bottom > 45 || bottom < 12) {
    return { ...DEFAULT_OUTER_LAYOUT };
  }

  return normalizeLayout({ main, bottom });
}

export function sanitizeHorizontalLayout(layout: PanelLayout): PanelLayout {
  const center = layout.center ?? 0;
  const explorer = layout.explorer ?? 0;
  const right = layout.right ?? 0;

  if (center < 40 || explorer > 30 || right > 35) {
    return { ...DEFAULT_HORIZONTAL_LAYOUT };
  }

  return normalizeLayout({ explorer, center, right });
}

function sanitizeStoredLayout(key: string, raw: string): PanelLayout | null {
  try {
    const parsed = JSON.parse(raw) as PanelLayout;
    if (!parsed || typeof parsed !== "object") return null;
    if (key === OUTER_STORAGE_KEY) return sanitizeOuterLayout(parsed);
    if (key === HORIZONTAL_STORAGE_KEY) return sanitizeHorizontalLayout(parsed);
    return parsed;
  } catch {
    return null;
  }
}

export const panelStorage = {
  getItem: (name: string) => {
    const raw = localStorage.getItem(name);
    if (!raw) return null;
    const sanitized = sanitizeStoredLayout(name, raw);
    if (!sanitized) {
      localStorage.removeItem(name);
      return null;
    }
    const next = JSON.stringify(sanitized);
    if (next !== raw) localStorage.setItem(name, next);
    return next;
  },
  setItem: (name: string, value: string) => {
    const sanitized = sanitizeStoredLayout(name, value);
    if (!sanitized) {
      localStorage.removeItem(name);
      return;
    }
    localStorage.setItem(name, JSON.stringify(sanitized));
  },
};

export function clearPanelLayouts() {
  localStorage.removeItem(HORIZONTAL_STORAGE_KEY);
  localStorage.removeItem(OUTER_STORAGE_KEY);
  localStorage.removeItem(LEGACY_BOTTOM_STORAGE_KEY);
}

/** @deprecated use DEFAULT_OUTER_LAYOUT */
export const DEFAULT_VERTICAL_LAYOUT = DEFAULT_OUTER_LAYOUT;
