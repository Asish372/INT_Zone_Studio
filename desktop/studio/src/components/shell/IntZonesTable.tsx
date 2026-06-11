import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { IntZone } from "../../types";

function zoneStatus(zone: IntZone, scene: ReturnType<typeof useWorkspaceStore.getState>["scene"]): string {
  const polys = scene?.polygons ?? [];
  const members = polys.filter((p) => zone.polygon_ids.includes(p.id) && p.status !== "deleted");
  if (!members.length) return "Empty";
  const pending = members.filter((p) => p.review_status === "pending" || p.review_status === "needs_review");
  if (pending.length) return "Review";
  const rejected = members.filter((p) => p.review_status === "rejected");
  if (rejected.length) return "Rejected";
  return "Ready";
}

export function IntZonesTable() {
  const tableBodyRef = useRef<HTMLTableSectionElement>(null);
  const zones = useWorkspaceStore((s) => s.zones);
  const scene = useWorkspaceStore((s) => s.scene);
  const collapsed = useWorkspaceStore((s) => s.tableCollapsed);
  const selectedZone = useWorkspaceStore((s) => s.selectedZone);
  const setTableCollapsed = useWorkspaceStore((s) => s.setTableCollapsed);
  const setSelectedZone = useWorkspaceStore((s) => s.setSelectedZone);

  useEffect(() => {
    if (!selectedZone) return;
    const row = tableBodyRef.current?.querySelector(
      `tr[data-zone-label="${CSS.escape(selectedZone)}"]`,
    );
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedZone, zones.length]);

  const onRowClick = (zone: IntZone) => {
    setSelectedZone(zone.label);
    const polys = scene?.polygons ?? [];
    const member = polys.find((p) => zone.polygon_ids.includes(p.id));
    if (member?.ring?.length) {
      window.dispatchEvent(
        new CustomEvent("studio:zoom-to-polygon", { detail: { id: member.id } }),
      );
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
          INT Zones ({zones.length}) {collapsed ? "▲" : "▼"}
        </button>
      </div>
      {!collapsed && (
        <div className="min-h-0 flex-1 overflow-auto">
          <table className="w-full text-left text-[11px]">
            <thead className="sticky top-0 z-10 bg-[var(--surface-panel)] text-[var(--text-secondary)]">
              <tr className="border-b border-[var(--border-default)]">
                <th className="px-2 py-1">Zone</th>
                <th className="px-2 py-1">Area</th>
                <th className="px-2 py-1">Face Count</th>
                <th className="px-2 py-1">Status</th>
              </tr>
            </thead>
            <tbody ref={tableBodyRef}>
              {zones.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-2 py-4 text-center text-[var(--text-muted)]">
                    Run detection, then generate INT zones from the Review menu.
                  </td>
                </tr>
              ) : (
                zones.map((zone) => {
                  const active = selectedZone === zone.label;
                  return (
                    <tr
                      key={zone.label}
                      data-zone-label={zone.label}
                      className={`cursor-pointer border-b border-[var(--border-default)] hover:bg-[var(--ribbon-hover)] ${
                        active ? "bg-[var(--brand-primary)]/10" : ""
                      }`}
                      onClick={() => onRowClick(zone)}
                    >
                      <td className="px-2 py-0.5 font-medium text-[var(--brand-primary)]">
                        {zone.label}
                      </td>
                      <td className="px-2 py-0.5">{zone.area_m2.toFixed(1)} m²</td>
                      <td className="px-2 py-0.5">{zone.face_count}</td>
                      <td className="px-2 py-0.5">{zoneStatus(zone, scene)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
