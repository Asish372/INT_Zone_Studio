import type { LoadProjectResult } from "../api/engine";
import { useWorkspaceStore } from "../stores/workspaceStore";
import type { Comment, UserRole } from "../types";

/** Restore workspace UI state after opening a saved .pjson project. */
export function applyProjectLoad(data: LoadProjectResult): void {
  const comments: Record<number, Comment[]> = {};
  for (const [key, value] of Object.entries(data.comments ?? {})) {
    const id = Number(key);
    if (!Number.isNaN(id)) comments[id] = value;
  }

  useWorkspaceStore.setState({
    comments,
    markups: data.markups ?? [],
    expectedPolygonCount:
      data.expected_polygon_count ?? data.counts.total ?? null,
    selectedId: null,
    selectedIds: [],
    selectedPolygon: null,
    activeProjectId: data.project_id ?? null,
    currentUser: data.current_user ?? useWorkspaceStore.getState().currentUser,
    currentRole: (data.current_role ??
      useWorkspaceStore.getState().currentRole) as UserRole,
  });
}
