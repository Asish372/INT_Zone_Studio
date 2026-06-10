import { useEffect, useRef, useState } from "react";
import { MENU_DEFINITIONS, MENU_TABS } from "../../shell/menuConfig";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { MenuTab, StudioCommandId } from "../../types";

interface MenuBarProps {
  onExecute: (command: StudioCommandId) => void;
}

export function MenuBar({ onExecute }: MenuBarProps) {
  const activeMenuTab = useWorkspaceStore((s) => s.activeMenuTab);
  const setActiveMenuTab = useWorkspaceStore((s) => s.setActiveMenuTab);
  const panelVisibility = useWorkspaceStore((s) => s.panelVisibility);
  const canvasOverlays = useWorkspaceStore((s) => s.canvasOverlays);
  const [openMenu, setOpenMenu] = useState<MenuTab | null>(null);
  const barRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!barRef.current?.contains(e.target as Node)) setOpenMenu(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenMenu(null);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const isChecked = (command?: StudioCommandId) => {
    if (!command) return false;
    if (command === "panel.toggle.explorer") return panelVisibility.explorer;
    if (command === "panel.toggle.table") return panelVisibility.table;
    if (command === "panel.toggle.properties") return panelVisibility.properties;
    if (command === "panel.toggle.validation") return panelVisibility.validation;
    if (command === "panel.toggle.audit") return panelVisibility.audit;
    if (command === "panel.toggle.console") return panelVisibility.console;
    if (command === "panel.toggle.minimap") return panelVisibility.minimap;
    if (command === "view.polygonIds.selected")
      return canvasOverlays.polygonIdMode === "selected";
    if (command === "view.polygonIds.visible")
      return canvasOverlays.polygonIdMode === "visible";
    if (command === "view.polygonIds.all")
      return canvasOverlays.polygonIdMode === "all";
    if (command === "view.polygonIds")
      return canvasOverlays.polygonIdMode === "visible";
    if (command === "view.vertices") return canvasOverlays.vertices;
    if (command === "view.labels") return canvasOverlays.labels;
    if (command === "view.coordinates") return canvasOverlays.coordinates;
    return false;
  };

  const menuDef = MENU_DEFINITIONS.find((m) => m.tab === openMenu);

  return (
    <nav className="menu-bar" ref={barRef}>
      {MENU_TABS.map((tab) => {
        const isActive = tab === activeMenuTab;
        const isOpen = tab === openMenu;
        return (
          <div key={tab} className="menu-bar-item-wrap">
            <button
              type="button"
              className={`menu-item ${isActive ? "menu-item-current" : ""} ${isOpen ? "menu-item-open" : ""}`}
              onClick={() => {
                setActiveMenuTab(tab);
                setOpenMenu(isOpen ? null : tab);
              }}
              onMouseEnter={() => {
                if (openMenu) setOpenMenu(tab);
              }}
            >
              {tab}
            </button>
            {isOpen && menuDef && (
              <div className="menu-dropdown" role="menu">
                {menuDef.groups.map((group) => (
                  <div key={group.label} className="menu-dropdown-group">
                    <div className="menu-dropdown-heading">{group.label}</div>
                    {group.items.map((item) =>
                      item.divider ? (
                        <div key={item.id} className="menu-dropdown-divider" />
                      ) : (
                        <button
                          key={item.id}
                          type="button"
                          role="menuitem"
                          className="menu-dropdown-item"
                          onClick={() => {
                            if (item.command) {
                              onExecute(item.command);
                            }
                            setOpenMenu(null);
                          }}
                        >
                          <span className="menu-dropdown-check">
                            {isChecked(item.command) ? "✓" : ""}
                          </span>
                          <span className="menu-dropdown-label">{item.label}</span>
                          {item.shortcut && (
                            <span className="menu-dropdown-shortcut">{item.shortcut}</span>
                          )}
                        </button>
                      ),
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}
