import { useEffect, useRef, useState } from "react";
import { selectPolygon } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";

export function GoToModal() {
  const open = useWorkspaceStore((s) => s.goToOpen);
  const mode = useWorkspaceStore((s) => s.goToMode);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const scene = useWorkspaceStore((s) => s.scene);
  const setGoToOpen = useWorkspaceStore((s) => s.setGoToOpen);
  const setSelected = useWorkspaceStore((s) => s.setSelected);
  const setPolygonSearch = useWorkspaceStore((s) => s.setPolygonSearch);
  const setTableCollapsed = useWorkspaceStore((s) => s.setTableCollapsed);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setValue("");
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open, mode]);

  if (!open) return null;

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed) return;

    if (mode === "polygon") {
      const id = Number.parseInt(trimmed.replace(/^#/, ""), 10);
      if (!Number.isFinite(id)) {
        setEngineError("Enter a polygon number (e.g. 182)");
        return;
      }
      const poly = scene?.polygons?.find((p) => p.id === id);
      if (!poly) {
        setEngineError(`Polygon #${id} not found`);
        return;
      }
      try {
        const selected = await selectPolygon(sessionId, id);
        setSelected(id, selected);
        setPolygonSearch(String(id));
        setTableCollapsed(false);
        window.dispatchEvent(
          new CustomEvent("studio:zoom-to-polygon", { detail: { id } }),
        );
        setGoToOpen(false);
      } catch (e) {
        setEngineError(e instanceof Error ? e.message : "Go to failed");
      }
      return;
    }

    const parts = trimmed.split(/[,\s]+/).map((p) => Number.parseFloat(p.trim()));
    if (parts.length < 2 || !Number.isFinite(parts[0]) || !Number.isFinite(parts[1])) {
      setEngineError("Enter coordinates as X, Y");
      return;
    }
    window.dispatchEvent(
      new CustomEvent("studio:go-to-coordinates", {
        detail: { x: parts[0], y: parts[1] },
      }),
    );
    setGoToOpen(false);
  };

  return (
    <div
      className="modal-overlay command-palette-overlay"
      onClick={() => setGoToOpen(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape") setGoToOpen(false);
        if (e.key === "Enter") void submit();
      }}
    >
      <div
        className="command-palette goto-modal"
        role="dialog"
        aria-label="Go To"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="goto-modal-title">
          {mode === "polygon" ? "Go to Polygon" : "Go to Coordinates"}
        </div>
        <input
          ref={inputRef}
          className="command-palette-input"
          placeholder={
            mode === "polygon" ? "Polygon #182" : "X, Y (e.g. 12500, 8400)"
          }
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void submit();
          }}
        />
        <div className="goto-modal-hint">
          {mode === "polygon"
            ? "Camera zooms to polygon and selects it in the table."
            : "Camera jumps to world coordinates."}
        </div>
        <div className="goto-modal-actions">
          <button type="button" className="btn-ghost text-xs" onClick={() => setGoToOpen(false)}>
            Cancel
          </button>
          <button type="button" className="btn-primary text-xs" onClick={() => void submit()}>
            Go
          </button>
        </div>
      </div>
    </div>
  );
}
