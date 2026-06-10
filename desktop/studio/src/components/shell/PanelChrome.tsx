import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";
import type { ReactNode } from "react";

interface PanelChromeProps {
  title: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
  orientation?: "horizontal" | "vertical";
  children: ReactNode;
}

export function PanelChrome({
  title,
  collapsed,
  onToggleCollapse,
  orientation = "vertical",
  children,
}: PanelChromeProps) {
  const CollapseIcon =
    orientation === "horizontal" ? ChevronLeft : ChevronDown;
  const ExpandIcon =
    orientation === "horizontal" ? ChevronRight : ChevronUp;

  if (collapsed) {
    return (
      <div
        className={`panel-chrome-collapsed panel-chrome-collapsed-${orientation}`}
        onClick={onToggleCollapse}
        onKeyDown={(e) => e.key === "Enter" && onToggleCollapse()}
        role="button"
        tabIndex={0}
        title={`Expand ${title}`}
      >
        <ExpandIcon size={14} className="shrink-0 opacity-70" />
        <span className="panel-chrome-collapsed-label">{title}</span>
      </div>
    );
  }

  return (
    <div className="panel-chrome">
      <div className="panel-chrome-header">
        <span className="panel-chrome-title">{title}</span>
        <button
          type="button"
          className="panel-chrome-collapse-btn"
          onClick={onToggleCollapse}
          title={`Collapse ${title}`}
          aria-label={`Collapse ${title}`}
        >
          <CollapseIcon size={14} />
        </button>
      </div>
      <div className="panel-chrome-body">{children}</div>
    </div>
  );
}
