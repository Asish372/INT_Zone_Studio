import type {
  ActionEntry,
  Comment,
  Counts,
  ExportResult,
  IntZone,
  Markup,
  PolygonRecord,
  ProjectMeta,
  ReviewStatus,
  SceneData,
  SeedPreview,
  Summary,
  UserRole,
  ValidationResult,
  WorkspaceSaveResult,
} from "../types";

const ENGINE_BASE =
  import.meta.env.VITE_ENGINE_URL ??
  (import.meta.env.DEV ? "/api" : "http://127.0.0.1:8765");

const SESSION_KEY = "int_zone_studio_session_id";

function headers(sessionId: string, json = false): HeadersInit {
  const h: Record<string, string> = { "X-Session-Id": sessionId };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data.detail ?? data);
  } catch {
    return res.statusText || "Request failed";
  }
}

export function getStoredSessionId(): string {
  return localStorage.getItem(SESSION_KEY) ?? "";
}

export function storeSessionId(id: string): void {
  localStorage.setItem(SESSION_KEY, id);
}

export async function waitForEngine(
  maxAttempts = 30,
  intervalMs = 500,
): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`${ENGINE_BASE}/health`);
      if (res.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(
    "Engine sidecar not reachable at " +
      ENGINE_BASE +
      ". Start it with: python scripts/run_polygon_workspace.py",
  );
}

export async function createSession(): Promise<string> {
  const res = await fetch(`${ENGINE_BASE}/session`, { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  storeSessionId(data.session_id);
  return data.session_id;
}

export async function ensureSession(): Promise<string> {
  let id = getStoredSessionId();
  if (!id) id = await createSession();
  return id;
}

export interface UploadResult {
  session_id: string;
  source_file: string;
  unit_label: string;
  scene: SceneData;
  counts: Counts;
  actions: ActionEntry[];
}

export async function uploadDrawing(
  sessionId: string,
  file: File,
): Promise<UploadResult> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${ENGINE_BASE}/upload`, {
    method: "POST",
    headers: headers(sessionId),
    body: fd,
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  if (data.session_id) storeSessionId(data.session_id);
  return data;
}

export async function fetchScene(
  sessionId: string,
): Promise<{ scene: SceneData; summary: Summary }> {
  const res = await fetch(`${ENGINE_BASE}/scene`, {
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchSummary(sessionId: string): Promise<Summary> {
  const res = await fetch(`${ENGINE_BASE}/summary`, {
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function selectPolygon(
  sessionId: string,
  polygonId: number | null,
): Promise<PolygonRecord | null> {
  const res = await fetch(`${ENGINE_BASE}/select`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ polygon_id: polygonId }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.selected ?? null;
}

export async function selectPolygons(
  sessionId: string,
  polygonIds: number[],
): Promise<{ selected_ids: number[]; selected: PolygonRecord[] }> {
  const res = await fetch(`${ENGINE_BASE}/select`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ polygon_ids: polygonIds }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function previewRecover(
  sessionId: string,
  x: number,
  y: number,
): Promise<SeedPreview> {
  const res = await fetch(`${ENGINE_BASE}/recover/preview`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ x, y }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.preview;
}

export async function confirmRecover(
  sessionId: string,
  x: number,
  y: number,
): Promise<{
  scene: SceneData;
  counts: Counts;
  actions: ActionEntry[];
  polygon: PolygonRecord;
  selected: PolygonRecord;
}> {
  const res = await fetch(`${ENGINE_BASE}/recover`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ x, y }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deletePolygon(
  sessionId: string,
  polygonId: number,
): Promise<{ scene: SceneData; counts: Counts; actions: ActionEntry[] }> {
  const res = await fetch(`${ENGINE_BASE}/polygon/${polygonId}/delete`, {
    method: "POST",
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function exportWorkspace(
  sessionId: string,
  formats: string[],
  useTimestamp = true,
): Promise<ExportResult> {
  const res = await fetch(`${ENGINE_BASE}/export`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ formats, use_timestamp: useTimestamp }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function saveWorkspace(
  sessionId: string,
  path: string,
): Promise<WorkspaceSaveResult> {
  const res = await fetch(`${ENGINE_BASE}/workspace/save`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export interface LoadProjectResult {
  session_id: string;
  source_file: string;
  unit_label: string;
  workspace_save_path: string | null;
  cad_available: boolean;
  scene: SceneData;
  counts: Counts;
  validation: ValidationResult | null;
  zones: IntZone[];
  comments?: Record<string, import("../types").Comment[]>;
  markups?: import("../types").Markup[];
  expected_polygon_count?: number | null;
  project_id?: string | null;
  current_user?: string;
  current_role?: string;
  actions: ActionEntry[];
}

export async function loadProjectFile(
  sessionId: string,
  file: File,
): Promise<LoadProjectResult> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${ENGINE_BASE}/workspace/load-project`, {
    method: "POST",
    headers: headers(sessionId),
    body: fd,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function openFolder(path: string): Promise<{ path: string }> {
  const res = await fetch(`${ENGINE_BASE}/open-folder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function runValidation(
  sessionId: string,
): Promise<{ validation: ValidationResult; actions: ActionEntry[] }> {
  const res = await fetch(`${ENGINE_BASE}/validate`, {
    method: "POST",
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function reviewPolygon(
  sessionId: string,
  polygonId: number,
  reviewStatus: ReviewStatus,
): Promise<{ polygon: PolygonRecord; scene: SceneData; actions: ActionEntry[] }> {
  const res = await fetch(`${ENGINE_BASE}/polygon/${polygonId}/review`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ review_status: reviewStatus }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function setExpectedCount(
  sessionId: string,
  count: number,
): Promise<void> {
  const res = await fetch(`${ENGINE_BASE}/expected-count`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ count }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function setUser(
  sessionId: string,
  user: string,
  role: UserRole,
): Promise<void> {
  const res = await fetch(`${ENGINE_BASE}/user`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ user, role }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function generateZones(
  sessionId: string,
): Promise<{ zones: IntZone[]; scene: SceneData; actions: ActionEntry[] }> {
  const res = await fetch(`${ENGINE_BASE}/zones/generate`, {
    method: "POST",
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function mergeZones(
  sessionId: string,
  zoneA: string,
  zoneB: string,
): Promise<{ zones: IntZone[]; scene: SceneData }> {
  const res = await fetch(`${ENGINE_BASE}/zones/merge`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ zone_a: zoneA, zone_b: zoneB }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function renameZone(
  sessionId: string,
  oldLabel: string,
  newLabel: string,
): Promise<{ zones: IntZone[]; scene: SceneData }> {
  const res = await fetch(`${ENGINE_BASE}/zones/rename`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ old_label: oldLabel, new_label: newLabel }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function undo(sessionId: string): Promise<{ scene: SceneData; counts: Counts }> {
  const res = await fetch(`${ENGINE_BASE}/undo`, {
    method: "POST",
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function redo(sessionId: string): Promise<{ scene: SceneData; counts: Counts }> {
  const res = await fetch(`${ENGINE_BASE}/redo`, {
    method: "POST",
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function addComment(
  sessionId: string,
  polygonId: number,
  text: string,
): Promise<Comment[]> {
  const res = await fetch(`${ENGINE_BASE}/polygon/${polygonId}/comment`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.comments;
}

export async function fetchComments(
  sessionId: string,
  polygonId: number,
): Promise<Comment[]> {
  const res = await fetch(`${ENGINE_BASE}/polygon/${polygonId}/comments`, {
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.comments;
}

export async function addMarkup(
  sessionId: string,
  x: number,
  y: number,
  text = "",
): Promise<Markup[]> {
  const res = await fetch(`${ENGINE_BASE}/markups`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ x, y, text }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.markups;
}

export async function fetchProjects(): Promise<ProjectMeta[]> {
  const res = await fetch(`${ENGINE_BASE}/projects`);
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.projects;
}

export async function createProject(name: string): Promise<ProjectMeta> {
  const res = await fetch(`${ENGINE_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.project;
}

export async function saveProjectVersion(
  sessionId: string,
  projectId: string,
  label?: string,
): Promise<ProjectMeta> {
  const res = await fetch(`${ENGINE_BASE}/projects/${projectId}/versions`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.project;
}

export async function loadProjectVersion(
  sessionId: string,
  projectId: string,
  versionId: string,
): Promise<{ scene: SceneData; counts: Counts; actions: ActionEntry[] }> {
  const res = await fetch(`${ENGINE_BASE}/projects/load-version`, {
    method: "POST",
    headers: headers(sessionId, true),
    body: JSON.stringify({ project_id: projectId, version_id: versionId }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function cloudSync(
  sessionId: string,
): Promise<{ path: string }> {
  const res = await fetch(`${ENGINE_BASE}/cloud/sync`, {
    method: "POST",
    headers: headers(sessionId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
