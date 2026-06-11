import { useEffect, type ReactNode, type RefObject } from "react";
import {
  Group,
  Panel,
  Separator,
  useDefaultLayout,
  useGroupRef,
  usePanelRef,
  type PanelImperativeHandle,
} from "react-resizable-panels";
import { ProjectExplorer } from "../shell/ProjectExplorer";
import { PropertiesPanel } from "../shell/PropertiesPanel";
import { ValidationSummary } from "../shell/ValidationSummary";
import { ViewerChrome } from "../shell/ViewerChrome";
import { ManualDrawBanner } from "../shell/ManualDrawBanner";
import { ManualPolygonBanner } from "../shell/ManualPolygonBanner";
import { BoundaryModeBanner } from "../shell/BoundaryModeBanner";
import { SeedBanner } from "../shell/SeedBanner";
import { PanelChrome } from "../shell/PanelChrome";
import { CadCanvas } from "../viewer/CadCanvas";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import {
  DEFAULT_HORIZONTAL_LAYOUT,
  DEFAULT_OUTER_LAYOUT,
  panelStorage,
} from "../../lib/panelLayout";
import { WorkspaceBottomDock } from "./WorkspaceBottomDock";
import type { PanelId } from "../../types";

function DockPanel({
  id,
  title,
  orientation,
  expanded,
  onToggle,
  panelRef,
  defaultSize,
  minSize,
  maxSize,
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
  maxSize?: number;
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
      maxSize={maxSize}
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

  const outerGroupRef = useGroupRef();
  const hGroupRef = useGroupRef();
  const explorerRef = usePanelRef();
  const rightRef = usePanelRef();

  useEffect(() => {
    const onReset = () => {
      outerGroupRef.current?.setLayout({ ...DEFAULT_OUTER_LAYOUT });
      hGroupRef.current?.setLayout({ ...DEFAULT_HORIZONTAL_LAYOUT });
    };
    window.addEventListener("studio:reset-panel-layout", onReset);
    return () => window.removeEventListener("studio:reset-panel-layout", onReset);
  }, [outerGroupRef, hGroupRef]);

  const outerLayout = useDefaultLayout({
    id: "int_zone_studio_panels_v",
    storage: panelStorage,
    panelIds: ["main", "bottom"],
  });

  const hLayout = useDefaultLayout({
    id: "int_zone_studio_panels_h",
    storage: panelStorage,
    panelIds: ["explorer", "center", "right"],
  });

  const toggle = (panel: PanelId) => () => togglePanel(panel);

  const rightExpanded =
    panels.properties || panels.validation || panels.audit;

  return (
    <div className="workspace-panels">
      <Group
        id="studio-outer"
        orientation="vertical"
        className="workspace-panels-group workspace-panels-group-outer"
        groupRef={outerGroupRef}
        defaultLayout={outerLayout.defaultLayout ?? DEFAULT_OUTER_LAYOUT}
        onLayoutChanged={outerLayout.onLayoutChanged}
      >
        <Panel id="main" defaultSize={72} minSize={45} className="panel-shell">
          <Group
            id="studio-h"
            orientation="horizontal"
            className="workspace-panels-group"
            groupRef={hGroupRef}
            defaultLayout={hLayout.defaultLayout ?? DEFAULT_HORIZONTAL_LAYOUT}
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

            <Panel id="center" defaultSize={73} minSize={40} className="panel-shell panel-canvas">
              <div className="workspace-center panel-content">
                <ViewerChrome />
                <SeedBanner />
                <BoundaryModeBanner />
                <ManualDrawBanner />
                <ManualPolygonBanner />
                <CadCanvas />
              </div>
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
        </Panel>

        <Separator className="resize-handle-h" />

        <Panel id="bottom" defaultSize={28} minSize={15} className="panel-shell panel-bottom-full">
          <div className="panel-content">
            <WorkspaceBottomDock />
          </div>
        </Panel>
      </Group>
    </div>
  );
}
