import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { SuspectedGapRegion } from "../../types";

function zoomToGap(gap: SuspectedGapRegion) {
  window.dispatchEvent(
    new CustomEvent("studio:zoom-to-region", {
      detail: { bbox: gap.bbox, center: gap.center },
    }),
  );
}

function recoverGap(gap: SuspectedGapRegion) {
  const [x, y] = gap.seed_point;
  const store = useWorkspaceStore.getState();
  if (!store.cadAvailable) {
    store.setEngineError("CAD source unavailable — seed recovery requires CAD geometry");
    return;
  }
  store.setSeedPreview(null, { x, y });
  store.setTool("add");
  zoomToGap(gap);
}

export function SuspectedGapsPanel() {
  const validation = useWorkspaceStore((s) => s.validation);
  const cadAvailable = useWorkspaceStore((s) => s.cadAvailable);

  const allGaps = validation?.suspected_gaps ?? [];
  const recoverable = allGaps.filter((g) => g.recoverable);
  const summary = validation?.gap_summary ?? {
    total: allGaps.length,
    recoverable: recoverable.length,
    informational: Math.max(0, allGaps.length - recoverable.length),
  };

  if (!validation) return null;

  return (
    <div className="suspected-gaps-panel border-t border-[var(--border-default)]">
      <div className="validation-title px-2 pt-2">Suspected Gaps</div>
      <p className="px-2 pb-2 text-[10px] text-[var(--text-muted)]">
        {summary.total} suspected gaps found ({summary.recoverable} recoverable,{" "}
        {summary.informational} informational)
      </p>
      {recoverable.length === 0 ? (
        <p className="px-2 pb-2 text-[10px] text-[var(--text-secondary)]">
          No recoverable gaps detected. Run validation after importing a drawing with open
          boundaries.
        </p>
      ) : (
        <ul className="max-h-48 overflow-y-auto text-[10px]">
          {recoverable.map((gap) => (
            <li
              key={gap.id}
              className="flex flex-wrap items-center gap-1 border-b border-[var(--border-default)] px-2 py-1.5"
            >
              <span className="min-w-0 flex-1 font-medium">{gap.id}</span>
              <span className="text-[var(--text-muted)]">
                {gap.area_estimate_m2 != null ? `${gap.area_estimate_m2} m²` : "—"}
              </span>
              <span className="text-[var(--text-muted)]">conf {gap.confidence}</span>
              <button
                type="button"
                className="btn-ghost px-1 py-0 text-[9px]"
                onClick={() => zoomToGap(gap)}
              >
                Zoom To
              </button>
              <button
                type="button"
                className="btn-ghost px-1 py-0 text-[9px]"
                disabled={!cadAvailable}
                onClick={() => recoverGap(gap)}
              >
                Recover
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
