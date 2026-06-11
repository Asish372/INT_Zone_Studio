import { useWorkspaceStore } from "../../stores/workspaceStore";

export function ManualDrawBanner() {
  const tool = useWorkspaceStore((s) => s.tool);
  const manualPolygonPreview = useWorkspaceStore((s) => s.manualPolygonPreview);
  const setTool = useWorkspaceStore((s) => s.setTool);
  const clearManualDraw = useWorkspaceStore((s) => s.clearManualDraw);

  if (tool !== "manual-draw" || manualPolygonPreview) return null;

  return (
    <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
      Draw Polygon: click vertices — Enter or double-click to close — click first vertex
      to close —{" "}
      <button
        type="button"
        className="underline"
        onClick={() => {
          clearManualDraw();
          setTool("select");
        }}
      >
        Esc to cancel
      </button>
    </div>
  );
}
