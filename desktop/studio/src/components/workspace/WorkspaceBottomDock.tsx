import { useEffect, useState } from "react";
import { BottomConsole } from "../shell/BottomConsole";
import { IntZonesTable } from "../shell/IntZonesTable";
import { PolygonTable } from "../shell/PolygonTable";
import { StatusFooter } from "../shell/StatusFooter";
import { useWorkspaceStore } from "../../stores/workspaceStore";

type BottomTableTab = "zones" | "polygons";

export function WorkspaceBottomDock() {
  const panels = useWorkspaceStore((s) => s.panelVisibility);
  const activeMenuTab = useWorkspaceStore((s) => s.activeMenuTab);
  const [tableTab, setTableTab] = useState<BottomTableTab>("polygons");

  useEffect(() => {
    if (activeMenuTab === "INT Zones" || activeMenuTab === "Review") {
      setTableTab("zones");
      return;
    }
    setTableTab("polygons");
  }, [activeMenuTab]);

  return (
    <div className="workspace-bottom-dock">
      {panels.table && (
        <div className="workspace-bottom-table">
          <div className="bottom-table-tabs">
            <button
              type="button"
              className={`bottom-table-tab ${tableTab === "polygons" ? "bottom-table-tab-active" : ""}`}
              onClick={() => setTableTab("polygons")}
            >
              Polygons
            </button>
            <button
              type="button"
              className={`bottom-table-tab ${tableTab === "zones" ? "bottom-table-tab-active" : ""}`}
              onClick={() => setTableTab("zones")}
            >
              INT Zones
            </button>
          </div>
          {tableTab === "zones" ? <IntZonesTable /> : <PolygonTable />}
        </div>
      )}
      <StatusFooter embedded />
      {panels.console && (
        <div className="workspace-bottom-console">
          <BottomConsole />
        </div>
      )}
    </div>
  );
}
