import { RIBBON_BY_TAB } from "../../shell/menuConfig";
import { CommandIcon } from "../icons/EngIcons";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { StudioCommandId } from "../../types";

const SCOPE_COMMANDS = new Set<StudioCommandId>([
  "detection.pickBoundary",
  "detection.autoBoundary",
  "detection.drawSlabBoundary",
  "detection.editBoundary",
  "detection.defineSlabBoundary",
  "detection.applyBoundary",
]);

const VIEW_LAYER_COMMANDS = new Set<StudioCommandId>([
  "view.cadDrawing",
  "view.intZones",
  "view.faces",
  "view.obstacles",
  "view.boundary",
  "view.labels",
]);

const VIEW_ID_COMMANDS = new Set<StudioCommandId>([
  "view.polygonIds.selected",
  "view.polygonIds.visible",
  "view.polygonIds.all",
]);

interface RibbonBarProps {
  onExecute: (command: StudioCommandId) => void;
}

export function RibbonBar({ onExecute }: RibbonBarProps) {
  const activeMenuTab = useWorkspaceStore((s) => s.activeMenuTab);
  const tool = useWorkspaceStore((s) => s.tool);
  const scopeEnabled = useWorkspaceStore((s) => s.scopeEnabled);
  const layers = useWorkspaceStore((s) => s.layers);
  const reviewMode = useWorkspaceStore((s) => s.reviewMode);
  const comparisonOverlay = useWorkspaceStore((s) => s.comparisonOverlay);
  const polygonIdMode = useWorkspaceStore((s) => s.canvasOverlays.polygonIdMode);
  const groups = RIBBON_BY_TAB[activeMenuTab] ?? [];

  const isLayerOn = (command: StudioCommandId) => {
    if (command === "view.cadDrawing") return layers.cad;
    if (command === "view.intZones") return layers.zones;
    if (command === "view.faces") return layers.faces;
    if (command === "view.obstacles") return layers.obstacles;
    if (command === "view.boundary") return layers.boundary;
    if (command === "view.labels") return layers.labels;
    return false;
  };

  const isActive = (command: StudioCommandId, toggle?: boolean) => {
    if (toggle || VIEW_LAYER_COMMANDS.has(command)) return isLayerOn(command);
    if (command === "view.polygonIds.selected") return polygonIdMode === "selected";
    if (command === "view.polygonIds.visible") return polygonIdMode === "visible";
    if (command === "view.polygonIds.all") return polygonIdMode === "all";
    if (VIEW_ID_COMMANDS.has(command)) return false;
    if (command === "tool.select") return tool === "select";
    if (command === "tool.rectSelect") return tool === "rect-select";
    if (command === "view.pan") return tool === "pan";
    if (command === "view.zoomWindow") return tool === "zoom-window";
    if (command === "detection.seedRecovery" || command === "detection.recoverMissing")
      return tool === "add";
    if (command === "detection.pickBoundary" || command === "detection.defineSlabBoundary")
      return tool === "scope-pick";
    if (command === "detection.autoBoundary") return tool === "scope-auto";
    if (command === "detection.drawSlabBoundary") return tool === "scope-draw";
    if (command === "detection.editBoundary") return tool === "scope-edit";
    if (command === "polygon.drawManual") return tool === "manual-draw";
    if (command === "review.mode") return reviewMode;
    if (command === "review.overlay") return comparisonOverlay;
    return false;
  };

  if (groups.length === 0) return null;

  return (
    <div className="ribbon-bar">
      {groups
        .map((group) => ({
          ...group,
          items: group.items.filter(
            (item) => !SCOPE_COMMANDS.has(item.command) || scopeEnabled,
          ),
        }))
        .filter((group) => group.items.length > 0)
        .map((group, gi) => (
        <div key={group.label} className="ribbon-group">
          <div className="ribbon-group-items">
            {group.items.map((item) => {
              const active = isActive(item.command, item.toggle);
              const isToggle =
                item.toggle ||
                VIEW_LAYER_COMMANDS.has(item.command) ||
                VIEW_ID_COMMANDS.has(item.command) ||
                item.command === "review.mode" ||
                item.command === "review.overlay";
              return (
                <button
                  key={item.id}
                  type="button"
                  title={`${item.label}${item.shortcut ? ` (${item.shortcut})` : ""}`}
                  className={`ribbon-btn ${active ? "ribbon-btn-active" : ""} ${isToggle ? "ribbon-btn-toggle" : ""}`}
                  onClick={() => onExecute(item.command)}
                >
                  <span className="ribbon-icon-wrap">
                    <CommandIcon command={item.command} size={17} />
                  </span>
                  <span className="ribbon-label">{item.label}</span>
                  {isToggle && (
                    <span className="ribbon-toggle-mark" aria-hidden>
                      {active ? "☑" : "☐"}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <div className="ribbon-group-label">{group.label}</div>
          {gi < groups.length - 1 && <div className="ribbon-group-sep" />}
        </div>
      ))}
    </div>
  );
}
