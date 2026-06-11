import { useWorkspaceStore } from "../../stores/workspaceStore";

export function LayerManagerModal() {
  const open = useWorkspaceStore((s) => s.layerManagerOpen);
  const setLayerManagerOpen = useWorkspaceStore((s) => s.setLayerManagerOpen);
  const layers = useWorkspaceStore((s) => s.layers);
  const setLayers = useWorkspaceStore((s) => s.setLayers);

  if (!open) return null;

  const rows = [
    { key: "cad" as const, name: "CAD Drawing", color: "#605e5c" },
    { key: "zones" as const, name: "INT Zones", color: "#06b6d4" },
    { key: "faces" as const, name: "Faces (Polygons)", color: "#06b6d4" },
    { key: "obstacles" as const, name: "Obstacles", color: "#f97316" },
    { key: "boundary" as const, name: "Boundary", color: "#a855f7" },
    { key: "labels" as const, name: "Labels", color: "#ffffff" },
  ];

  return (
    <div className="modal-overlay">
      <div className="modal-card max-w-md">
        <header className="modal-header">
          <h2 className="text-lg font-semibold">Layer Visibility</h2>
          <button
            type="button"
            className="text-xl"
            onClick={() => setLayerManagerOpen(false)}
          >
            ×
          </button>
        </header>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[var(--border-default)] text-[var(--text-secondary)]">
              <th className="p-2 text-left">Visible</th>
              <th className="p-2 text-left">Layer</th>
              <th className="p-2 text-left">Color</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-b border-[var(--border-default)]">
                <td className="p-2">
                  <input
                    type="checkbox"
                    checked={layers[row.key]}
                    onChange={(e) => setLayers({ [row.key]: e.target.checked })}
                  />
                </td>
                <td className="p-2">{row.name}</td>
                <td className="p-2">
                  <span
                    className="inline-block h-3 w-3 rounded-sm"
                    style={{ background: row.color }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <footer className="border-t border-[var(--border-default)] p-3">
          <button
            type="button"
            className="btn-primary"
            onClick={() => setLayerManagerOpen(false)}
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}
