import { setExpectedCount } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";

export function ReviewModePanel() {
  const reviewMode = useWorkspaceStore((s) => s.reviewMode);
  const comparisonOverlay = useWorkspaceStore((s) => s.comparisonOverlay);
  const counts = useWorkspaceStore((s) => s.counts);
  const expectedPolygonCount = useWorkspaceStore((s) => s.expectedPolygonCount);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const setReviewMode = useWorkspaceStore((s) => s.setReviewMode);
  const setComparisonOverlay = useWorkspaceStore((s) => s.setComparisonOverlay);
  const setExpectedPolygonCount = useWorkspaceStore((s) => s.setExpectedPolygonCount);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);

  if (!reviewMode) return null;

  const expected = expectedPolygonCount ?? counts.total;
  const detected = counts.total;
  const missing = Math.max(0, expected - detected);

  const onSetExpected = async () => {
    const val = prompt("AutoCAD expected polygon count:", String(expected));
    if (!val) return;
    const n = parseInt(val, 10);
    if (isNaN(n)) return;
    try {
      await setExpectedCount(sessionId, n);
      setExpectedPolygonCount(n);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Failed to set count");
    }
  };

  return (
    <div className="review-mode-bar flex items-center gap-4 border-b border-[var(--border-default)] bg-[rgba(0,120,212,0.08)] px-4 py-2 text-xs">
      <strong>Review Mode</strong>
      <span>
        AutoCAD: <strong>{expected}</strong>
      </span>
      <span className="text-green-600">
        Detected: <strong>{detected}</strong>
      </span>
      <span className={missing > 0 ? "text-red-500" : "text-green-600"}>
        Missing: <strong>{missing}</strong>
      </span>
      <label className="flex items-center gap-1">
        <input
          type="checkbox"
          checked={comparisonOverlay}
          onChange={(e) => setComparisonOverlay(e.target.checked)}
        />
        Green = Detected overlay
      </label>
      <button type="button" className="btn-ghost text-[10px]" onClick={() => void onSetExpected()}>
        Set Expected Count
      </button>
      <button type="button" className="btn-ghost ml-auto text-[10px]" onClick={() => setReviewMode(false)}>
        Exit Review
      </button>
    </div>
  );
}
