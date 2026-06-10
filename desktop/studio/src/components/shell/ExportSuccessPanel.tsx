import { openFolder } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";

async function revealFolder(folder: string) {
  try {
    const opener = await import("@tauri-apps/plugin-opener");
    await opener.openPath(folder);
    return;
  } catch {
    /* not in Tauri */
  }
  await openFolder(folder);
}

export function ExportSuccessPanel() {
  const open = useWorkspaceStore((s) => s.exportSuccessOpen);
  const result = useWorkspaceStore((s) => s.lastExportResult);
  const setExportSuccessOpen = useWorkspaceStore((s) => s.setExportSuccessOpen);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const setStudioToast = useWorkspaceStore((s) => s.setStudioToast);

  if (!open || !result) return null;

  const entries = Object.entries(result.absolute_paths ?? result.paths);
  const folder = result.folder ?? entries[0]?.[1]?.replace(/[/\\][^/\\]+$/, "");
  const summary = result.summary;

  const onCopyPath = async () => {
    if (!folder) return;
    try {
      await navigator.clipboard.writeText(folder);
      setStudioToast("Folder path copied");
      window.setTimeout(() => setStudioToast(null), 2000);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Copy failed");
    }
  };

  const onOpenFolder = async () => {
    if (!folder) return;
    try {
      await revealFolder(folder);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Could not open folder");
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card max-w-lg">
        <header className="modal-header">
          <h2 className="text-lg font-semibold">Export Complete</h2>
          <button
            type="button"
            className="text-xl leading-none"
            onClick={() => setExportSuccessOpen(false)}
          >
            ×
          </button>
        </header>
        <div className="space-y-3 p-4">
          {summary && (
            <p className="text-sm text-[var(--status-pass)]">
              Exported {summary.file_count} file(s) · {summary.polygon_count} polygons ·{" "}
              {summary.formats.join(", ")}
            </p>
          )}
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[var(--border-default)] text-[var(--text-muted)]">
                <th className="py-1 pr-2">Format</th>
                <th className="py-1">Path</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([fmt, path]) => (
                <tr key={fmt} className="border-b border-[var(--border-default)]/50">
                  <td className="py-1 pr-2 font-medium uppercase">{fmt}</td>
                  <td className="break-all py-1 text-[var(--text-secondary)]">{path}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {folder && (
            <p className="text-[10px] text-[var(--text-muted)]">Output folder: {folder}</p>
          )}
        </div>
        <footer className="flex justify-end gap-2 border-t border-[var(--border-default)] p-3">
          <button type="button" className="btn-ghost" onClick={() => void onCopyPath()}>
            Copy Path
          </button>
          <button type="button" className="btn-ghost" onClick={() => void onOpenFolder()}>
            Open Folder
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => setExportSuccessOpen(false)}
          >
            Done
          </button>
        </footer>
      </div>
    </div>
  );
}
