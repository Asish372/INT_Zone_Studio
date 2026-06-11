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
        {(counts.manual_added ?? 0) > 0 && (
          <>
            <span className="viewer-stat-sep">|</span>
            <span>
              Manual: <strong className="text-violet-400">{counts.manual_added}</strong>
            </span>
          </>
        )}
        <span className="viewer-stat-sep">|</span>
        <span>
          Total: <strong>{counts.total}</strong>
        </span>
        {(counts.obstacles ?? 0) > 0 && (
          <>
            <span className="viewer-stat-sep">|</span>
            <span>
              Obstacles: <strong className="text-orange-500">{counts.obstacles}</strong>
            </span>
          </>
        )}
      </div>
    </div>
  );
}
