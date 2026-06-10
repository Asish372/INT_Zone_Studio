import { BUILD_LABEL } from "../../lib/buildInfo";
import { useWorkspaceStore } from "../../stores/workspaceStore";

export function StatusFooter() {
  const coords = useWorkspaceStore((s) => s.coords);
  const unitLabel = useWorkspaceStore((s) => s.unitLabel);
  const sourceFile = useWorkspaceStore((s) => s.sourceFile);
  const counts = useWorkspaceStore((s) => s.counts);
  const selectedId = useWorkspaceStore((s) => s.selectedId);
  const tool = useWorkspaceStore((s) => s.tool);

  const toolLabel =
    tool === "select"
      ? "Select"
      : tool === "rect-select"
        ? "Rect Select"
        : tool === "pan"
          ? "Pan"
          : tool === "zoom-window"
            ? "Zoom"
            : tool === "add"
              ? "Seed Recovery"
              : "Ready";

  return (
    <footer className="status-footer">
      <span className="status-tool">{toolLabel}</span>
      <span className="status-coords">
        {coords.x.toFixed(1)}, {coords.y.toFixed(1)} {unitLabel}
      </span>
      <span className="hidden sm:inline max-w-[140px] truncate">
        {sourceFile || "No drawing"}
      </span>
      <span>Polygons: {counts.total}</span>
      <span>Selected: {selectedId != null ? `#${selectedId}` : "—"}</span>
      <span className="hidden md:inline text-[var(--text-secondary)]">{BUILD_LABEL}</span>
      <span className="status-ready">Ready</span>
    </footer>
  );
}
