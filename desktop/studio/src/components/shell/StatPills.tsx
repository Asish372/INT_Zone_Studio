import { useWorkspaceStore } from "../../stores/workspaceStore";

export function StatPills() {
  const counts = useWorkspaceStore((s) => s.counts);
  const zones = useWorkspaceStore((s) => s.zones);
  const sourceFile = useWorkspaceStore((s) => s.sourceFile);

  if (!sourceFile) return null;

  return (
    <div className="engineer-stats-bar">
      <span>
        Detected Faces:{" "}
        <strong className="text-[var(--polygon-auto)]">{counts.detected}</strong>
      </span>
      <span>
        Manual Added:{" "}
        <strong className="text-violet-400">{counts.manual_added ?? 0}</strong>
      </span>
      <span>
        Obstacles:{" "}
        <strong className="text-orange-500">{counts.obstacles ?? 0}</strong>
      </span>
      <span>
        INT Zones: <strong className="text-[var(--brand-primary)]">{zones.length}</strong>
      </span>
    </div>
  );
}
