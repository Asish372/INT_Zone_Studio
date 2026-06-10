import { FileText } from "lucide-react";
import { useWorkspaceStore } from "../../stores/workspaceStore";

export function ViewerChrome() {
  const sourceFile = useWorkspaceStore((s) => s.sourceFile);
  const counts = useWorkspaceStore((s) => s.counts);

  if (!sourceFile) return null;

  return (
    <div className="viewer-chrome">
      <div className="viewer-tab">
        <FileText size={14} className="viewer-tab-icon shrink-0 opacity-80" />
        <span className="truncate">{sourceFile}</span>
      </div>
      <div className="viewer-stats">
        <span>
          Detected: <strong className="stat-cyan">{counts.detected}</strong>
        </span>
        <span className="viewer-stat-sep">|</span>
        <span>
          Seed: <strong className="stat-green">{counts.seed_added}</strong>
        </span>
        <span className="viewer-stat-sep">|</span>
        <span>
          Total: <strong>{counts.total}</strong>
        </span>
      </div>
    </div>
  );
}
