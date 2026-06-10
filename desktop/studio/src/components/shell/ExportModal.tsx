import { exportWorkspace } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";

const OPTIONS = [
  {
    formats: ["dxf"],
    title: "Export Polygons (DXF)",
    desc: "Closed polylines on DETECTED_REGIONS layer",
    primary: false,
  },
  {
    formats: ["csv"],
    title: "Export Schedule (CSV)",
    desc: "Area, perimeter, centroid per polygon",
    primary: false,
  },
  {
    formats: ["xlsx"],
    title: "Export Schedule (Excel)",
    desc: "Full polygon schedule with zones and status",
    primary: false,
  },
  {
    formats: ["json"],
    title: "Export to JSON",
    desc: "Polygon rings + metadata",
    primary: false,
  },
  {
    formats: ["pdf"],
    title: "Detection Report (PDF)",
    desc: "Validation summary + polygon schedule",
    primary: false,
  },
  {
    formats: ["zones_dxf"],
    title: "INT Zones (DXF)",
    desc: "Zone polygons on INT_ZONES layer",
    primary: false,
  },
  {
    formats: ["package"],
    title: "Export Project Package",
    desc: "PDF + DXF + CSV + Excel in one click",
    primary: true,
  },
  {
    formats: ["json", "dxf", "csv"],
    title: "Export All (JSON + DXF + CSV)",
    desc: "Timestamped files in output/polygon_workspace",
    primary: false,
  },
];

export function ExportModal() {
  const open = useWorkspaceStore((s) => s.exportOpen);
  const setExportOpen = useWorkspaceStore((s) => s.setExportOpen);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const counts = useWorkspaceStore((s) => s.counts);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const setLastExportResult = useWorkspaceStore((s) => s.setLastExportResult);
  const setExportSuccessOpen = useWorkspaceStore((s) => s.setExportSuccessOpen);

  if (!open) return null;

  const canExport = counts.total > 0;

  const runExport = async (formats: string[]) => {
    if (!canExport) {
      setEngineError("No active polygons to export");
      return;
    }
    setExportOpen(false);
    try {
      const data = await exportWorkspace(sessionId, formats);
      setActions(data.actions);
      setLastExportResult(data);
      setExportSuccessOpen(true);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Export failed");
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <header className="modal-header">
          <h2 className="text-lg font-semibold">Export & Reports</h2>
          <button
            type="button"
            className="text-xl leading-none"
            onClick={() => setExportOpen(false)}
          >
            ×
          </button>
        </header>
        {!canExport && (
          <p className="border-b border-[var(--border-default)] px-4 py-2 text-xs text-amber-400">
            No active polygons to export. Import a drawing or restore a workspace first.
          </p>
        )}
        <div className="space-y-2 p-4">
          {OPTIONS.map((opt) => (
            <button
              key={opt.title}
              type="button"
              disabled={!canExport}
              className={`export-option w-full text-left ${opt.primary ? "export-option-primary" : ""} disabled:opacity-50`}
              onClick={() => void runExport(opt.formats)}
            >
              <strong className="block">{opt.title}</strong>
              <span className="text-xs text-[var(--text-secondary)]">{opt.desc}</span>
            </button>
          ))}
        </div>
        <footer className="border-t border-[var(--border-default)] p-3">
          <button type="button" className="btn-ghost" onClick={() => setExportOpen(false)}>
            Cancel
          </button>
        </footer>
      </div>
    </div>
  );
}
