import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { runValidation } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import { SuspectedGapsPanel } from "./SuspectedGapsPanel";

export function ValidationSummary() {
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const validation = useWorkspaceStore((s) => s.validation);
  const setValidation = useWorkspaceStore((s) => s.setValidation);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const scene = useWorkspaceStore((s) => s.scene);
  const cadAvailable = useWorkspaceStore((s) => s.cadAvailable);

  const counts = validation?.counts ?? {
    open_boundaries: 0,
    self_intersections: 0,
    gaps: 0,
    overlaps: 0,
    duplicates: 0,
    tiny_polygons: 0,
  };

  const items = [
    { label: "Open Boundaries", key: "open_boundaries" as const },
    { label: "Self Intersections", key: "self_intersections" as const },
    { label: "Gaps", key: "gaps" as const },
    { label: "Overlaps", key: "overlaps" as const },
    { label: "Duplicates", key: "duplicates" as const },
    { label: "Tiny Polygons", key: "tiny_polygons" as const },
  ];

  const onRun = async () => {
    try {
      const data = await runValidation(sessionId);
      setValidation(data.validation);
      setActions(data.actions);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Validation failed");
    }
  };

  return (
    <div className="validation-panel">
      <div className="validation-title">Validation Center</div>
      <ul className="validation-list">
        {items.map((item) => {
          const val = counts[item.key];
          const warn = item.key === "tiny_polygons" ? val > 0 : val > 0;
          const Icon = warn ? AlertTriangle : CheckCircle2;
          return (
            <li key={item.label} className="validation-row">
              <Icon
                size={12}
                className={warn ? "text-[var(--status-warn)]" : "text-[var(--status-pass)]"}
              />
              <span>{item.label}</span>
              <span className="validation-count">{val}</span>
            </li>
          );
        })}
      </ul>
      {validation && (
        <div className="px-2 pb-1 text-[10px] text-[var(--text-muted)]">
          {validation.ok ? (
            <span className="text-[var(--status-pass)]">All critical checks passed</span>
          ) : (
            <span className="text-[var(--status-warn)]">
              {validation.issues.length} issue(s) found
            </span>
          )}
        </div>
      )}
      <button
        type="button"
        disabled={!scene || !cadAvailable}
        onClick={() => void onRun()}
        className="btn-ghost validation-run w-full text-[10px]"
        title={!cadAvailable ? "CAD source required for gap validation" : undefined}
      >
        Run Validation
      </button>
      <SuspectedGapsPanel />
    </div>
  );
}
