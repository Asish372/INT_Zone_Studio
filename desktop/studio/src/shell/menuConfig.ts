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
  toggle?: boolean;
}

export interface RibbonGroupDef {
  label: string;
  items: RibbonItemDef[];
}

export const MENU_TABS: MenuTab[] = [
  "Home",
  "Detection",
  "Review",
  "View",
  "INT Zones",
  "Help",
];

export const MENU_DEFINITIONS: MenuDef[] = [
  {
    tab: "Home",
    groups: [
      {
        label: "Project",
        items: [
          { id: "home-import", label: "Import Drawing", command: "file.importDxf" },
          { id: "home-open", label: "Open Project", command: "file.openProject", shortcut: "Ctrl+O" },
          { id: "home-new", label: "New Project", command: "file.newProject" },
          { id: "home-save", label: "Save", command: "file.save", shortcut: "Ctrl+S" },
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
          { id: "home-export-pkg", label: "Export Package", command: "export.fullPackage" },
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
        label: "Scope",
        items: [
          { id: "det-pick-scope", label: "Pick Boundary", command: "detection.pickBoundary", shortcut: "B" },
          { id: "det-auto-scope", label: "Auto Detect Boundary", command: "detection.autoBoundary" },
          { id: "det-draw-scope", label: "Draw Boundary", command: "detection.drawSlabBoundary" },
          { id: "det-edit-scope", label: "Edit Boundary", command: "detection.editBoundary" },
          { id: "det-apply-scope", label: "Apply Boundary", command: "detection.applyBoundary" },
        ],
      },
      {
        label: "Recovery",
        items: [
          { id: "det-seed", label: "Seed Recovery", command: "detection.seedRecovery", shortcut: "R" },
          { id: "det-recover", label: "Recover Missing Polygon", command: "detection.recoverMissing" },
          { id: "det-manual", label: "Draw Polygon (Manual)", command: "polygon.drawManual", shortcut: "M" },
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
      {
        label: "INT Zones",
        items: [
          { id: "rev-zones-gen", label: "Generate INT Zones", command: "zones.generate" },
          { id: "rev-zones-rebuild", label: "Rebuild INT Zones", command: "zones.rebuild" },
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
        label: "Layers",
        items: [
          { id: "view-cad", label: "CAD Drawing", command: "view.cadDrawing" },
          { id: "view-zones", label: "INT Zones", command: "view.intZones" },
          { id: "view-faces", label: "Faces (Polygons)", command: "view.faces" },
          { id: "view-obstacles", label: "Obstacles", command: "view.obstacles" },
          { id: "view-boundary", label: "Boundary", command: "view.boundary" },
          { id: "view-labels", label: "Labels", command: "view.labels" },
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
  {
    tab: "Help",
    groups: [
      {
        label: "Pilot",
        items: [
          {
            id: "help-export-feedback",
            label: "Export Pilot Feedback Template",
            command: "help.exportPilotFeedback",
          },
        ],
      },
      {
        label: "Reference",
        items: [
          { id: "help-shortcuts", label: "Keyboard Shortcuts", command: "help.shortcuts" },
          { id: "help-system", label: "System Info", command: "help.systemInfo" },
          { id: "help-about", label: "About", command: "help.about" },
        ],
      },
    ],
  },
];

export const RIBBON_BY_TAB: Record<MenuTab, RibbonGroupDef[]> = {
  Home: [
    {
      label: "Project",
      items: [
        { id: "r-import", label: "Import Drawing", command: "file.importDxf" },
        { id: "r-open", label: "Open Project", command: "file.openProject", shortcut: "O" },
        { id: "r-save", label: "Save", command: "file.save", shortcut: "S" },
        { id: "r-export-pkg", label: "Export Package", command: "export.fullPackage" },
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
        { id: "r-run", label: "Run Detection", command: "detection.run", shortcut: "D" },
        { id: "r-rerun", label: "Re-run Detection", command: "detection.rerun" },
        { id: "r-all", label: "Detect All", command: "detection.all" },
      ],
    },
    {
      label: "Scope",
      items: [
        { id: "r-pick-scope", label: "Pick Boundary", command: "detection.pickBoundary", shortcut: "B" },
        { id: "r-auto-scope", label: "Auto Detect Boundary", command: "detection.autoBoundary" },
        { id: "r-draw-scope", label: "Draw Boundary", command: "detection.drawSlabBoundary" },
        { id: "r-edit-scope", label: "Edit Boundary", command: "detection.editBoundary" },
        { id: "r-apply-scope", label: "Apply Boundary", command: "detection.applyBoundary" },
      ],
    },
    {
      label: "Recover",
      items: [
        { id: "r-seed", label: "Seed Recovery", command: "detection.seedRecovery", shortcut: "R" },
        { id: "r-missing", label: "Recover Missing", command: "detection.recoverMissing" },
        { id: "r-manual", label: "Draw Polygon (Manual)", command: "polygon.drawManual", shortcut: "M" },
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
        { id: "r-rect", label: "Rect Select", command: "tool.rectSelect" },
        { id: "r-find", label: "Find Polygon", command: "polygon.find" },
      ],
    },
    {
      label: "Review",
      items: [
        { id: "r-approve", label: "Approve", command: "polygon.approve" },
        { id: "r-reject", label: "Reject", command: "polygon.reject" },
        { id: "r-needs", label: "Needs Review", command: "polygon.needsReview" },
        { id: "r-delete", label: "Delete", command: "polygon.delete" },
      ],
    },
    {
      label: "Mode",
      items: [
        { id: "r-rev-mode", label: "Review Mode", command: "review.mode", toggle: true },
        { id: "r-overlay", label: "Overlay", command: "review.overlay", toggle: true },
      ],
    },
    {
      label: "INT Zones",
      items: [
        { id: "r-zone-gen", label: "Generate Zones", command: "zones.generate" },
        { id: "r-zone-rebuild", label: "Rebuild Zones", command: "zones.rebuild" },
      ],
    },
  ],
  View: [
    {
      label: "Navigate",
      items: [
        { id: "r-pan", label: "Pan", command: "view.pan", shortcut: "P" },
        { id: "r-zoom", label: "Zoom Window", command: "view.zoomWindow", shortcut: "Z" },
        { id: "r-fit", label: "Fit View", command: "view.fit", shortcut: "F" },
      ],
    },
    {
      label: "Layers",
      items: [
        { id: "r-cad", label: "CAD Drawing", command: "view.cadDrawing", toggle: true },
        { id: "r-zones", label: "INT Zones", command: "view.intZones", toggle: true },
        { id: "r-faces", label: "Faces", command: "view.faces", toggle: true },
        { id: "r-obstacles", label: "Obstacles", command: "view.obstacles", toggle: true },
        { id: "r-boundary", label: "Boundary", command: "view.boundary", toggle: true },
        { id: "r-labels", label: "Labels", command: "view.labels", toggle: true },
        { id: "r-layer-mgr", label: "Layer Manager", command: "panel.toggle.layers" },
      ],
    },
    {
      label: "IDs",
      items: [
        { id: "r-ids-selected", label: "Selected IDs", command: "view.polygonIds.selected", toggle: true },
        { id: "r-ids-visible", label: "Visible IDs", command: "view.polygonIds.visible", toggle: true },
        { id: "r-ids-all", label: "All IDs", command: "view.polygonIds.all", toggle: true },
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
        { id: "r-zone-gen-tab", label: "Generate", command: "zones.generate" },
        { id: "r-zone-rebuild-tab", label: "Rebuild", command: "zones.rebuild" },
      ],
    },
    {
      label: "Export",
      items: [
        { id: "r-zone-dxf", label: "Zones DXF", command: "export.zonesDxf" },
      ],
    },
  ],
  Help: [],
};
