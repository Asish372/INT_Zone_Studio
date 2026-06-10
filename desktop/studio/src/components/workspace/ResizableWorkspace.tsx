import { useEffect, type ReactNode, type RefObject } from "react";
import {
  Group,
  Panel,
  Separator,
  useDefaultLayout,
  usePanelRef,
  type PanelImperativeHandle,
} from "react-resizable-panels";
import { ProjectExplorer } from "../shell/ProjectExplorer";
import { PropertiesPanel } from "../shell/PropertiesPanel";
import { ValidationSummary } from "../shell/ValidationSummary";
import { PolygonTable } from "../shell/PolygonTable";
import { ViewerChrome } from "../shell/ViewerChrome";
import { SeedBanner } from "../shell/SeedBanner";
import { BottomConsole } from "../shell/BottomConsole";
import { PanelChrome } from "../shell/PanelChrome";
import { CadCanvas } from "../viewer/CadCanvas";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { PanelId } from "../../types";

const panelStorage = {
  getItem: (name: string) => localStorage.getItem(name),
  setItem: (name: string, value: string) => localStorage.setItem(name, value),
};

function DockPanel({
  id,
  title,
  orientation,
  expanded,
  onToggle,
  panelRef,
  defaultSize,
  minSize,
  collapsedSize,
  children,
}: {
  id: string;
  title: string;
  orientation: "horizontal" | "vertical";
  expanded: boolean;
  onToggle: () => void;
  panelRef: RefObject<PanelImperativeHandle | null>;
  defaultSize: number;
  minSize: number;
  collapsedSize: number;
  children: ReactNode;
}) {
  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    if (expanded) {
      if (panel.isCollapsed()) panel.expand();
    } else if (!panel.isCollapsed()) {
      panel.collapse();
    }
  }, [expanded, panelRef]);

  return (
    <Panel
      id={id}
      panelRef={panelRef}
      defaultSize={defaultSize}
      minSize={minSize}
      collapsible
      collapsedSize={collapsedSize}
      className="panel-shell"
    >
      <PanelChrome
        title={title}
        collapsed={!expanded}
        onToggleCollapse={onToggle}
        orientation={orientation}
      >
        {children}
      </PanelChrome>
    </Panel>
  );
}

export function ResizableWorkspace() {
  const panels = useWorkspaceStore((s) => s.panelVisibility);
  const togglePanel = useWorkspaceStore((s) => s.togglePanel);

  const explorerRef = usePanelRef();
  const rightRef = usePanelRef();
  const tableRef = usePanelRef();
  const consoleRef = usePanelRef();

  const hLayout = useDefaultLayout({
    id: "int_zone_studio_panels_h",
    storage: panelStorage,
    panelIds: ["explorer", "center", "right"],
  });

  const vLayout = useDefaultLayout({
    id: "int_zone_studio_panels_v",
    storage: panelStorage,
    panelIds: ["canvas", "table", "console"],
  });

  const toggle = (panel: PanelId) => () => togglePanel(panel);

  const rightExpanded =
    panels.properties || panels.validation || panels.audit;

  return (
    <div className="workspace-panels">
      <Group
        id="studio-h"
        orientation="horizontal"
        className="workspace-panels-group"
        defaultLayout={hLayout.defaultLayout ?? { explorer: 11, center: 73, right: 16 }}
        onLayoutChanged={hLayout.onLayoutChanged}
      >
        <DockPanel
          id="explorer"
          title="Explorer"
          orientation="horizontal"
          expanded={panels.explorer}
          onToggle={toggle("explorer")}
          panelRef={explorerRef}
          defaultSize={11}
          minSize={10}
          collapsedSize={3}
        >
          <ProjectExplorer />
        </DockPanel>

        <Separator className="resize-handle-v" />

        <Panel id="center" defaultSize={73} minSize={45} className="panel-shell">
          <Group
            id="studio-v"
            orientation="vertical"
            className="workspace-panels-group workspace-panels-group-vertical"
            defaultLayout={vLayout.defaultLayout ?? { canvas: 72, table: 20, console: 8 }}
            onLayoutChanged={vLayout.onLayoutChanged}
          >
            <Panel id="canvas" defaultSize={72} minSize={50} className="panel-shell panel-canvas">
              <div className="workspace-center panel-content">
                <ViewerChrome />
                <SeedBanner />
                <CadCanvas />
              </div>
            </Panel>

            <Separator className="resize-handle-h" />

            <DockPanel
              id="table"
              title="Polygon Table"
              orientation="vertical"
              expanded={panels.table}
              onToggle={toggle("table")}
              panelRef={tableRef}
              defaultSize={20}
              minSize={12}
              collapsedSize={6}
            >
              <div className="panel-content panel-content-table">
                <PolygonTable />
              </div>
            </DockPanel>

            <Separator className="resize-handle-h" />

            <DockPanel
              id="console"
              title="Messages"
              orientation="vertical"
              expanded={panels.console}
              onToggle={toggle("console")}
              panelRef={consoleRef}
              defaultSize={8}
              minSize={8}
              collapsedSize={6}
            >
              <div className="panel-content">
                <BottomConsole />
              </div>
            </DockPanel>
          </Group>
        </Panel>

        <Separator className="resize-handle-v" />

        <DockPanel
          id="right"
          title="Inspector"
          orientation="horizontal"
          expanded={rightExpanded}
          onToggle={() => {
            const st = useWorkspaceStore.getState();
            const any = st.panelVisibility.properties;
            st.setPanelVisibility({
              properties: !any,
              validation: !any,
              audit: false,
            });
          }}
          panelRef={rightRef}
          defaultSize={16}
          minSize={12}
          collapsedSize={3}
        >
          <div className="panel-content workspace-right flex flex-col">
            {panels.properties && <PropertiesPanel />}
            {panels.validation && <ValidationSummary />}
          </div>
        </DockPanel>
      </Group>
    </div>
  );
}
