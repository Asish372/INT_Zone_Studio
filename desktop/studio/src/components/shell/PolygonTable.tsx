import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import { selectPolygon } from "../../api/engine";
import { filterPolygons } from "../../viewer/geometry";
import type { PolygonFilter, PolygonRecord } from "../../types";

const FILTERS: { id: PolygonFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "auto", label: "Auto" },
  { id: "recovered", label: "Recovered" },
  { id: "manual", label: "Manual" },
  { id: "deleted", label: "Deleted" },
  { id: "large", label: "Large (>100)" },
  { id: "small", label: "Small (<5)" },
  { id: "approved", label: "Approved" },
  { id: "pending", label: "Pending" },
];

export function PolygonTable() {
  const tableBodyRef = useRef<HTMLTableSectionElement>(null);
  const scene = useWorkspaceStore((s) => s.scene);
  const selectedId = useWorkspaceStore((s) => s.selectedId);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const collapsed = useWorkspaceStore((s) => s.tableCollapsed);
  const polygonFilter = useWorkspaceStore((s) => s.polygonFilter);
  const polygonSearch = useWorkspaceStore((s) => s.polygonSearch);
  const validation = useWorkspaceStore((s) => s.validation);
  const setTableCollapsed = useWorkspaceStore((s) => s.setTableCollapsed);
  const setSelected = useWorkspaceStore((s) => s.setSelected);
  const setPolygonFilter = useWorkspaceStore((s) => s.setPolygonFilter);
  const setPolygonSearch = useWorkspaceStore((s) => s.setPolygonSearch);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);

  const allPolygons = scene?.polygons ?? [];
  const polygons = filterPolygons(allPolygons, polygonFilter, polygonSearch);

  useEffect(() => {
    if (selectedId == null) return;
    const row = tableBodyRef.current?.querySelector(
      `tr[data-polygon-id="${selectedId}"]`,
    );
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedId, polygons.length]);

  const onRowClick = async (poly: PolygonRecord) => {
    try {
      const selected = await selectPolygon(sessionId, poly.id);
      setSelected(poly.id, selected);
      window.dispatchEvent(
        new CustomEvent("studio:zoom-to-polygon", { detail: { id: poly.id } }),
      );
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Select failed");
    }
  };

  return (
    <div className="flex h-full w-full min-h-0 flex-col bg-[var(--surface-panel)]">
      <div className="flex shrink-0 items-center gap-2 border-b border-[var(--border-default)] px-2 py-1">
        <button
          type="button"
          className="text-xs font-semibold hover:text-[var(--brand-primary)]"
          onClick={() => setTableCollapsed(!collapsed)}
        >
          Polygon Table ({polygons.length}) {collapsed ? "▲" : "▼"}
        </button>
        <input
          type="search"
          placeholder="Find #182 or area..."
          className="ml-auto w-40 rounded border border-[var(--border-default)] bg-transparent px-2 py-0.5 text-[10px]"
          value={polygonSearch}
          onChange={(e) => setPolygonSearch(e.target.value)}
        />
      </div>
      {!collapsed && (
        <>
          <div className="flex shrink-0 flex-wrap gap-1 px-2 py-1">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                className={`rounded px-2 py-0.5 text-[10px] ${
                  polygonFilter === f.id
                    ? "bg-[var(--brand-primary)] text-white"
                    : "bg-[var(--ribbon-hover)]"
                }`}
                onClick={() => setPolygonFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-auto">
            <table className="w-full text-left text-[11px]">
              <thead className="sticky top-0 bg-[var(--surface-chrome)]">
                <tr>
                  <th className="px-2 py-1">ID</th>
                  <th className="px-2 py-1">Source</th>
                  <th className="px-2 py-1">Status</th>
                  <th className="px-2 py-1">Area</th>
                  <th className="px-2 py-1">Perimeter</th>
                  <th className="px-2 py-1">Layer</th>
                  <th className="px-2 py-1">INT Zone</th>
                  <th className="px-2 py-1">Creator</th>
                </tr>
              </thead>
              <tbody ref={tableBodyRef}>
                {polygons.map((p, i) => (
                  <tr
                    key={p.id}
                    data-polygon-id={p.id}
                    className={`cursor-pointer hover:bg-[var(--ribbon-hover)] ${
                      p.id === selectedId
                        ? "bg-[rgba(0,120,212,0.12)]"
                        : i % 2
                          ? "bg-[var(--table-row-alt)]"
                          : ""
                    }`}
                    onClick={() => void onRowClick(p)}
                  >
                    <td className="px-2 py-0.5 font-mono">{p.id}</td>
                    <td className="px-2 py-0.5 capitalize">{p.source}</td>
                    <td className="px-2 py-0.5 capitalize">
                      {p.review_status ?? "pending"}
                    </td>
                    <td className="px-2 py-0.5">{p.area_m2?.toFixed(2)}</td>
                    <td className="px-2 py-0.5">{p.perimeter_m?.toFixed(2)}</td>
                    <td className="px-2 py-0.5">{p.layer ?? "—"}</td>
                    <td className="px-2 py-0.5">{p.int_zone ?? "—"}</td>
                    <td className="px-2 py-0.5">{p.created_by ?? "System"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {validation && validation.issues.length > 0 && (
            <div className="max-h-20 shrink-0 overflow-auto border-t border-[var(--border-default)] px-2 py-1">
              <div className="text-[10px] font-semibold">Validation Issues</div>
              {validation.issues.slice(0, 10).map((issue, i) => (
                <div key={i} className="text-[10px] text-[var(--status-warn)]">
                  {issue.message}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
