import type { MenuTab, StudioCommandId } from "../types";

export interface MenuItemDef {
  id: string;
  label: string;
  command?: StudioCommandId;
  shortcut?: string;
  divider?: boolean;
}

export interface MenuGroupDef {
  label: string;
  items: MenuItemDef[];
}

export interface MenuDef {
  tab: MenuTab;
  groups: MenuGroupDef[];
}

export interface RibbonItemDef {
  id: string;
  label: string;
  command: StudioCommandId;
  shortcut?: string;
}

export interface RibbonGroupDef {
  label: string;
  items: RibbonItemDef[];
}

/** Only tabs with shipped, working commands. */
export const MENU_TABS: MenuTab[] = [
  "Home",
  "Detection",
  "Review",
  "View",
  "INT Zones",
];

export const MENU_DEFINITIONS: MenuDef[] = [
  {
    tab: "Home",
    groups: [
      {
        label: "Project",
        items: [
          { id: "home-open", label: "Open Project", command: "file.openProject", shortcut: "Ctrl+O" },
          { id: "home-new", label: "New Project", command: "file.newProject" },
          { id: "home-save", label: "Save Workspace", command: "file.save", shortcut: "Ctrl+S" },
          { id: "home-save-as", label: "Save Workspace As", command: "file.saveAs" },
          { id: "home-version", label: "Save Version", command: "file.saveVersion" },
          { id: "home-settings", label: "Project Settings", command: "file.projectSettings" },
        ],
      },
      {
        label: "Import",
        items: [
          { id: "home-import-dxf", label: "Import DXF", command: "file.importDxf" },
          { id: "home-import-dwg", label: "Import DWG", command: "file.importDwg" },
        ],
      },
      {
        label: "Export",
        items: [
          { id: "home-export", label: "Export", command: "export.open" },
          { id: "home-export-dxf", label: "Export DXF", command: "export.dxf" },
          { id: "home-export-excel", label: "Export Excel", command: "export.excel" },
          { id: "home-export-pkg", label: "Full Package", command: "export.fullPackage" },
        ],
      },
      {
        label: "Edit",
        items: [
          { id: "home-undo", label: "Undo", command: "edit.undo", shortcut: "Ctrl+Z" },
          { id: "home-redo", label: "Redo", command: "edit.redo", shortcut: "Ctrl+Y" },
        ],
      },
    ],
  },
  {
    tab: "Detection",
    groups: [
      {
        label: "Detection",
        items: [
          { id: "det-run", label: "Run Detection", command: "detection.run", shortcut: "D" },
          { id: "det-rerun", label: "Re-run Detection", command: "detection.rerun" },
          { id: "det-all", label: "Detect All", command: "detection.all" },
        ],
      },
      {
        label: "Recovery",
        items: [
          { id: "det-seed", label: "Seed Recovery", command: "detection.seedRecovery", shortcut: "R" },
          { id: "det-recover", label: "Recover Missing Polygon", command: "detection.recoverMissing" },
        ],
      },
      {
        label: "Validation",
        items: [
          { id: "det-validate", label: "Validate", command: "review.validate", shortcut: "V" },
        ],
      },
      {
        label: "Statistics",
        items: [
          { id: "det-count", label: "Detected Count", command: "detection.stats.detected" },
          { id: "det-missing", label: "Missing Count", command: "detection.stats.missing" },
          { id: "det-coverage", label: "Coverage %", command: "detection.stats.coverage" },
        ],
      },
    ],
  },
  {
    tab: "Review",
    groups: [
      {
        label: "Selection",
        items: [
          { id: "rev-select", label: "Select", command: "tool.select", shortcut: "S" },
          { id: "rev-rect", label: "Rectangle Select", command: "tool.rectSelect" },
          { id: "rev-find", label: "Find Polygon", command: "polygon.find", shortcut: "Ctrl+G" },
        ],
      },
      {
        label: "Status",
        items: [
          { id: "rev-approve", label: "Approve", command: "polygon.approve" },
          { id: "rev-reject", label: "Reject", command: "polygon.reject" },
          { id: "rev-review", label: "Needs Review", command: "polygon.needsReview" },
          { id: "rev-delete", label: "Delete", command: "polygon.delete", shortcut: "Del" },
        ],
      },
      {
        label: "Review Mode",
        items: [
          { id: "rev-mode", label: "Toggle Review Mode", command: "review.mode" },
          { id: "rev-overlay", label: "Comparison Overlay", command: "review.overlay" },
          { id: "rev-validate", label: "Run Validation", command: "review.validate" },
          { id: "rev-errors", label: "Review Errors", command: "review.errors" },
          { id: "rev-warnings", label: "Review Warnings", command: "review.warnings" },
        ],
      },
    ],
  },
  {
    tab: "View",
    groups: [
      {
        label: "Navigation",
        items: [
          { id: "view-pan", label: "Pan", command: "view.pan", shortcut: "P" },
          { id: "view-zoom", label: "Zoom Window", command: "view.zoomWindow", shortcut: "Z" },
          { id: "view-fit", label: "Fit View", command: "view.fit", shortcut: "F" },
          { id: "view-goto", label: "Go to Coordinates", command: "view.goToCoordinates" },
        ],
      },
      {
        label: "Drawing",
        items: [
          { id: "view-poly-ids-selected", label: "Show Selected IDs", command: "view.polygonIds.selected" },
          { id: "view-poly-ids-visible", label: "Show Visible IDs", command: "view.polygonIds.visible" },
          { id: "view-poly-ids-all", label: "Show All IDs", command: "view.polygonIds.all" },
          { id: "view-vertices", label: "Vertices", command: "view.vertices" },
          { id: "view-coords", label: "Coordinates", command: "view.coordinates" },
        ],
      },
      {
        label: "Panels",
        items: [
          { id: "view-explorer", label: "Explorer", command: "panel.toggle.explorer" },
          { id: "view-table", label: "Polygon Table", command: "panel.toggle.table" },
          { id: "view-properties", label: "Properties", command: "panel.toggle.properties" },
          { id: "view-validation", label: "Validation", command: "panel.toggle.validation" },
          { id: "view-console", label: "Messages", command: "panel.toggle.console" },
          { id: "view-layers", label: "Layer Manager", command: "panel.toggle.layers" },
          { id: "view-minimap", label: "Minimap", command: "panel.toggle.minimap" },
        ],
      },
      {
        label: "Theme",
        items: [
          { id: "view-theme-dark", label: "Dark", command: "view.theme.dark" },
          { id: "view-theme-light", label: "Light", command: "view.theme.light" },
          { id: "view-theme-auto", label: "System", command: "view.theme.auto" },
        ],
      },
      {
        label: "Layout",
        items: [
          { id: "view-layout-default", label: "Default Layout", command: "layout.default" },
          { id: "view-layout-review", label: "Review Layout", command: "layout.review" },
          { id: "view-layout-detection", label: "Detection Layout", command: "layout.detection" },
          { id: "view-layout-reset", label: "Reset Layout", command: "layout.reset" },
        ],
      },
    ],
  },
  {
    tab: "INT Zones",
    groups: [
      {
        label: "Generate",
        items: [
          { id: "zone-gen", label: "Generate Zones", command: "zones.generate" },
          { id: "zone-rebuild", label: "Rebuild Zones", command: "zones.rebuild" },
        ],
      },
      {
        label: "Analysis",
        items: [
          { id: "zone-area", label: "Zone Area", command: "zones.area" },
          { id: "zone-count", label: "Zone Count", command: "zones.count" },
          { id: "zone-poly-count", label: "Polygon Count", command: "zones.polygonCount" },
        ],
      },
      {
        label: "Export",
        items: [
          { id: "zone-export-dxf", label: "Export Zones DXF", command: "export.zonesDxf" },
        ],
      },
    ],
  },
];

export const RIBBON_BY_TAB: Record<MenuTab, RibbonGroupDef[]> = {
  Home: [
    {
      label: "File",
      items: [
        { id: "r-open", label: "Open Project", command: "file.openProject", shortcut: "O" },
        { id: "r-save", label: "Save", command: "file.save", shortcut: "S" },
        { id: "r-import", label: "Import DXF", command: "file.importDxf" },
        { id: "r-export", label: "Export", command: "export.open" },
      ],
    },
    {
      label: "Edit",
      items: [
        { id: "r-undo", label: "Undo", command: "edit.undo" },
        { id: "r-redo", label: "Redo", command: "edit.redo" },
      ],
    },
  ],
  Detection: [
    {
      label: "Detect",
      items: [
        { id: "r-run", label: "Run", command: "detection.run", shortcut: "D" },
        { id: "r-rerun", label: "Re-run", command: "detection.rerun" },
        { id: "r-all", label: "All", command: "detection.all" },
      ],
    },
    {
      label: "Recover",
      items: [
        { id: "r-seed", label: "Seed", command: "detection.seedRecovery", shortcut: "R" },
        { id: "r-missing", label: "Missing", command: "detection.recoverMissing" },
      ],
    },
    {
      label: "Validate",
      items: [
        { id: "r-val", label: "Validate", command: "review.validate", shortcut: "V" },
      ],
    },
  ],
  Review: [
    {
      label: "Select",
      items: [
        { id: "r-select", label: "Select", command: "tool.select", shortcut: "S" },
        { id: "r-rect", label: "Rect", command: "tool.rectSelect" },
        { id: "r-find", label: "Find", command: "polygon.find" },
      ],
    },
    {
      label: "Review",
      items: [
        { id: "r-approve", label: "Approve", command: "polygon.approve" },
        { id: "r-reject", label: "Reject", command: "polygon.reject" },
        { id: "r-needs", label: "Review", command: "polygon.needsReview" },
      ],
    },
    {
      label: "Mode",
      items: [
        { id: "r-rev-mode", label: "Review Mode", command: "review.mode" },
        { id: "r-overlay", label: "Overlay", command: "review.overlay" },
      ],
    },
  ],
  View: [
    {
      label: "Zoom",
      items: [
        { id: "r-zoom", label: "Zoom", command: "view.zoomWindow", shortcut: "Z" },
        { id: "r-fit", label: "Fit", command: "view.fit", shortcut: "F" },
        { id: "r-pan", label: "Pan", command: "view.pan", shortcut: "P" },
      ],
    },
    {
      label: "Layers",
      items: [
        { id: "r-layers", label: "Layers", command: "panel.toggle.layers" },
        { id: "r-ids-selected", label: "Selected IDs", command: "view.polygonIds.selected" },
        { id: "r-ids-visible", label: "Visible IDs", command: "view.polygonIds.visible" },
        { id: "r-ids-all", label: "All IDs", command: "view.polygonIds.all" },
      ],
    },
    {
      label: "Theme",
      items: [
        { id: "r-dark", label: "Dark", command: "view.theme.dark" },
        { id: "r-light", label: "Light", command: "view.theme.light" },
      ],
    },
  ],
  "INT Zones": [
    {
      label: "Generate",
      items: [
        { id: "r-zone-gen", label: "Generate", command: "zones.generate" },
        { id: "r-zone-rebuild", label: "Rebuild", command: "zones.rebuild" },
      ],
    },
    {
      label: "Export",
      items: [
        { id: "r-zone-dxf", label: "Zones DXF", command: "export.zonesDxf" },
      ],
    },
  ],
};
