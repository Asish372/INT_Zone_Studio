import { BUILD_LABEL } from "../../lib/buildInfo";
import { useWorkspaceStore } from "../../stores/workspaceStore";

export function StatusFooter({ embedded = false }: { embedded?: boolean }) {
  const coords = useWorkspaceStore((s) => s.coords);
  const unitLabel = useWorkspaceStore((s) => s.unitLabel);
  const sourceFile = useWorkspaceStore((s) => s.sourceFile);

  return (
    <footer className={`status-footer ${embedded ? "status-footer-embedded" : ""}`}>
      <span className="status-file max-w-[180px] truncate" title={sourceFile || undefined}>
        {sourceFile || "No drawing"}
      </span>
      <span className="status-coords">
        X: {coords.x.toFixed(1)} | Y: {coords.y.toFixed(1)} | Z: 0
      </span>
      <span className="status-shortcuts hidden lg:inline">
        A Seed · S Select · P Pan · F Fit · Del Delete · Ctrl+S Save
      </span>
      <span className="status-meta ml-auto flex items-center gap-3">
        <span>Units: {unitLabel}</span>
        <span className="hidden sm:inline">Scale: 1:100</span>
        {!embedded && <span className="hidden md:inline text-[var(--text-secondary)]">{BUILD_LABEL}</span>}
        <span className="status-ready">Ready</span>
      </span>
    </footer>
  );
}
