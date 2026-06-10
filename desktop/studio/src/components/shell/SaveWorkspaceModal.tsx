import { useEffect, useState } from "react";
import { saveWorkspace } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";

const LAST_SAVE_DIR_KEY = "int_zone_studio_last_save_dir";

function defaultSavePath(sourceFile: string, existingPath: string | null): string {
  if (existingPath) return existingPath;
  const stem = sourceFile ? sourceFile.replace(/\.[^.]+$/, "") : "workspace";
  const lastDir = localStorage.getItem(LAST_SAVE_DIR_KEY);
  const base = lastDir || "";
  return base ? `${base}\\${stem}.pjson` : `${stem}.pjson`;
}

export function SaveWorkspaceModal() {
  const open = useWorkspaceStore((s) => s.saveWorkspaceOpen);
  const saveAs = useWorkspaceStore((s) => s.saveWorkspaceAs);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const sourceFile = useWorkspaceStore((s) => s.sourceFile);
  const workspaceSavePath = useWorkspaceStore((s) => s.workspaceSavePath);
  const setSaveWorkspaceOpen = useWorkspaceStore((s) => s.setSaveWorkspaceOpen);
  const setWorkspaceSavePath = useWorkspaceStore((s) => s.setWorkspaceSavePath);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const setStudioToast = useWorkspaceStore((s) => s.setStudioToast);

  const [path, setPath] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setPath(defaultSavePath(sourceFile, saveAs ? null : workspaceSavePath));
    }
  }, [open, sourceFile, workspaceSavePath, saveAs]);

  if (!open) return null;

  const onSave = async () => {
    const trimmed = path.trim();
    if (!trimmed) {
      setEngineError("Enter a full path for the workspace file (.pjson)");
      return;
    }
    setSaving(true);
    try {
      const data = await saveWorkspace(sessionId, trimmed);
      setWorkspaceSavePath(data.path);
      const dir = data.path.replace(/[/\\][^/\\]+$/, "");
      if (dir) localStorage.setItem(LAST_SAVE_DIR_KEY, dir);
      setActions(data.actions);
      setSaveWorkspaceOpen(false);
      setStudioToast(`Workspace saved to ${data.path}`);
      window.setTimeout(() => {
        if (useWorkspaceStore.getState().studioToast?.includes(data.path)) {
          setStudioToast(null);
        }
      }, 3200);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card max-w-lg">
        <header className="modal-header">
          <h2 className="text-lg font-semibold">
            {saveAs ? "Save Workspace As" : "Save Workspace"}
          </h2>
          <button
            type="button"
            className="text-xl leading-none"
            onClick={() => setSaveWorkspaceOpen(false)}
          >
            ×
          </button>
        </header>
        <div className="space-y-3 p-4">
          <p className="text-xs text-[var(--text-secondary)]">
            Choose where to save your workspace (.pjson). This file includes polygons,
            zones, reviews, comments, and validation results.
          </p>
          <label className="block text-xs font-medium">Full path</label>
          <input
            type="text"
            className="w-full rounded border border-[var(--border-default)] bg-[var(--surface-panel)] px-3 py-2 text-sm"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="C:\Projects\MyDrawing.pjson"
            autoFocus
          />
        </div>
        <footer className="flex justify-end gap-2 border-t border-[var(--border-default)] p-3">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setSaveWorkspaceOpen(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={saving}
            onClick={() => void onSave()}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </footer>
      </div>
    </div>
  );
}
