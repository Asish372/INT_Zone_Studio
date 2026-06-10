import { useWorkspaceStore } from "../../stores/workspaceStore";

export function ReviewOnlyBanner() {
  const cadAvailable = useWorkspaceStore((s) => s.cadAvailable);
  const scene = useWorkspaceStore((s) => s.scene);

  if (cadAvailable || !scene) return null;

  return (
    <div className="review-only-banner border-b border-amber-600/40 bg-amber-500/10 px-4 py-2 text-xs text-amber-100">
      Original CAD source not available. Polygon workspace loaded in review-only mode.
      Recovery and CAD-based validation are unavailable.
    </div>
  );
}
