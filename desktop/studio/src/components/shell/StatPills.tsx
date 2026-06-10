import { useWorkspaceStore } from "../../stores/workspaceStore";

export function StatPills() {
  const counts = useWorkspaceStore((s) => s.counts);
  const expectedPolygonCount = useWorkspaceStore((s) => s.expectedPolygonCount);
  const zones = useWorkspaceStore((s) => s.zones);
  const hoverId = useWorkspaceStore((s) => s.hoverId);
  const scene = useWorkspaceStore((s) => s.scene);

  const expected = expectedPolygonCount ?? counts.total;
  const missing = Math.max(0, expected - counts.total);
  const hoverPoly = scene?.polygons?.find((p) => p.id === hoverId);

  return (
    <div className="flex flex-wrap items-center justify-center gap-4 border-b border-[var(--border-default)] bg-[var(--surface-chrome)] py-1.5 text-sm">
      <span>
        Detected: <strong className="text-[var(--polygon-auto)]">{counts.detected}</strong>
      </span>
      <span>
        Seed: <strong className="text-[var(--polygon-seed)]">{counts.seed_added}</strong>
      </span>
      <span>
        Deleted: <strong className="text-[var(--polygon-deleted)]">{counts.deleted}</strong>
      </span>
      <span>
        Total: <strong>{counts.total}</strong>
      </span>
      {expectedPolygonCount != null && (
        <span className={missing > 0 ? "text-red-500" : "text-green-600"}>
          Missing: <strong>{missing}</strong> (expected {expected})
        </span>
      )}
      {zones.length > 0 && (
        <span>
          INT Zones: <strong>{zones.length}</strong>
        </span>
      )}
      {hoverPoly && (
        <span className="text-[var(--brand-primary)]">
          #{hoverPoly.id}: {hoverPoly.area_m2?.toFixed(2)} m², {hoverPoly.perimeter_m?.toFixed(2)} m
        </span>
      )}
    </div>
  );
}
