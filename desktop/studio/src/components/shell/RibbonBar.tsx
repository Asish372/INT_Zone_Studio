import { RIBBON_BY_TAB } from "../../shell/menuConfig";
import { CommandIcon } from "../icons/EngIcons";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { StudioCommandId } from "../../types";

interface RibbonBarProps {
  onExecute: (command: StudioCommandId) => void;
}

export function RibbonBar({ onExecute }: RibbonBarProps) {
  const activeMenuTab = useWorkspaceStore((s) => s.activeMenuTab);
  const tool = useWorkspaceStore((s) => s.tool);
  const groups = RIBBON_BY_TAB[activeMenuTab] ?? [];

  const isActive = (command: StudioCommandId) => {
    if (command === "tool.select") return tool === "select";
    if (command === "tool.rectSelect") return tool === "rect-select";
    if (command === "view.pan") return tool === "pan";
    if (command === "view.zoomWindow") return tool === "zoom-window";
    if (command === "detection.seedRecovery") return tool === "add";
    return false;
  };

  return (
    <div className="ribbon-bar">
      {groups.map((group, gi) => (
        <div key={group.label} className="ribbon-group">
          <div className="ribbon-group-items">
            {group.items.map((item) => {
              const active = isActive(item.command);
              return (
                <button
                  key={item.id}
                  type="button"
                  title={`${item.label}${item.shortcut ? ` (${item.shortcut})` : ""}`}
                  className={`ribbon-btn ${active ? "ribbon-btn-active" : ""}`}
                  onClick={() => onExecute(item.command)}
                >
                  <span className="ribbon-icon-wrap">
                    <CommandIcon command={item.command} size={17} />
                  </span>
                  <span className="ribbon-label">{item.label}</span>
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
