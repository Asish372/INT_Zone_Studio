import type { ReactNode } from "react";
import type { StudioCommandId } from "../../types";

interface IconProps {
  size?: number;
  className?: string;
}

const stroke = 1.65;

function Svg({
  size = 20,
  className,
  children,
}: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden
    >
      {children}
    </svg>
  );
}

export function IconOpen({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M4 8V6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2" stroke="currentColor" strokeWidth={stroke} />
      <path d="M4 12h16" stroke="currentColor" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconSave({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M6 4h10l4 4v12H6V4z" stroke="currentColor" strokeWidth={stroke} />
      <path d="M14 4v4H8V4" stroke="currentColor" strokeWidth={stroke} />
      <rect x="8" y="13" width="8" height="6" stroke="currentColor" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconImport({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M12 4v10M8 10l4 4 4-4" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <path d="M4 18h16" stroke="currentColor" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconExport({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M12 14V4M8 8l4-4 4 4" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <path d="M4 18h16" stroke="currentColor" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconDetect({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <rect x="3" y="3" width="18" height="18" rx="1" stroke="currentColor" strokeWidth={stroke} strokeDasharray="3 2" />
      <path d="M8 16l3-4 3 2 4-6" stroke="#06b6d4" strokeWidth={stroke} strokeLinecap="round" />
    </Svg>
  );
}

export function IconSeed({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <circle cx="12" cy="12" r="3" stroke="#22c55e" strokeWidth={stroke} />
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" stroke="currentColor" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconValidate({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M12 3l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V7l8-4z" stroke="currentColor" strokeWidth={stroke} />
      <path d="M9 12l2 2 4-4" stroke="#22c55e" strokeWidth={stroke} strokeLinecap="round" />
    </Svg>
  );
}

export function IconPolygon({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M6 18L4 8l8-3 8 3-2 10H6z" stroke="#06b6d4" strokeWidth={stroke} fill="rgba(6,182,212,0.12)" />
    </Svg>
  );
}

export function IconSelect({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M5 4l4 14 2-6 6-2L5 4z" stroke="currentColor" strokeWidth={stroke} fill="rgba(255,255,255,0.08)" />
    </Svg>
  );
}

export function IconRectSelect({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <rect x="5" y="7" width="14" height="12" stroke="currentColor" strokeWidth={stroke} strokeDasharray="3 2" />
    </Svg>
  );
}

export function IconApprove({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <circle cx="12" cy="12" r="9" stroke="#22c55e" strokeWidth={stroke} />
      <path d="M8 12l3 3 5-6" stroke="#22c55e" strokeWidth={stroke} strokeLinecap="round" />
    </Svg>
  );
}

export function IconReject({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <circle cx="12" cy="12" r="9" stroke="#ef4444" strokeWidth={stroke} />
      <path d="M9 9l6 6M15 9l-6 6" stroke="#ef4444" strokeWidth={stroke} strokeLinecap="round" />
    </Svg>
  );
}

export function IconZoom({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <circle cx="10" cy="10" r="6" stroke="currentColor" strokeWidth={stroke} />
      <path d="M15 15l5 5" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <rect x="7" y="7" width="6" height="6" stroke="currentColor" strokeWidth={1.2} strokeDasharray="2 1" />
    </Svg>
  );
}

export function IconFit({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <rect x="8" y="8" width="8" height="8" stroke="currentColor" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconPan({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M8 12V6.5a1.5 1.5 0 0 1 3 0V11" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <path d="M11 11V5a1.5 1.5 0 0 1 3 0v8" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <path d="M14 13V8a1.5 1.5 0 0 1 3 0v7.5a5 5 0 0 1-10 0V11" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
    </Svg>
  );
}

export function IconLayers({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M12 4l9 5-9 5-9-5 9-5z" stroke="currentColor" strokeWidth={stroke} />
      <path d="M3 12l9 5 9-5M3 16l9 5 9-5" stroke="currentColor" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconZone({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <rect x="3" y="5" width="8" height="8" stroke="#06b6d4" strokeWidth={stroke} />
      <rect x="13" y="5" width="8" height="8" stroke="#06b6d4" strokeWidth={stroke} />
      <rect x="8" y="13" width="8" height="8" stroke="#06b6d4" strokeWidth={stroke} />
    </Svg>
  );
}

export function IconUndo({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <path d="M6 8H14a5 5 0 0 1 0 10H12" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <path d="M9 5L6 8l3 3" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
    </Svg>
  );
}

export function IconFind({ size, className }: IconProps) {
  return (
    <Svg size={size} className={className}>
      <circle cx="10" cy="10" r="6" stroke="currentColor" strokeWidth={stroke} />
      <path d="M15 15l5 5" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      <text x="10" y="12" textAnchor="middle" fontSize="7" fill="currentColor" fontFamily="monospace">#</text>
    </Svg>
  );
}

const COMMAND_ICONS: Partial<
  Record<StudioCommandId, (props: IconProps) => ReactNode>
> = {
  "file.openProject": IconOpen,
  "file.importDxf": IconImport,
  "file.importDwg": IconImport,
  "file.save": IconSave,
  "file.saveAs": IconSave,
  "file.saveVersion": IconSave,
  "export.open": IconExport,
  "export.dxf": IconExport,
  "export.excel": IconExport,
  "export.fullPackage": IconExport,
  "export.zonesDxf": IconExport,
  "detection.run": IconDetect,
  "detection.rerun": IconDetect,
  "detection.all": IconDetect,
  "detection.seedRecovery": IconSeed,
  "detection.recoverMissing": IconSeed,
  "review.validate": IconValidate,
  "tool.select": IconSelect,
  "tool.rectSelect": IconRectSelect,
  "polygon.approve": IconApprove,
  "polygon.reject": IconReject,
  "polygon.needsReview": IconValidate,
  "polygon.find": IconFind,
  "view.zoomWindow": IconZoom,
  "view.fit": IconFit,
  "view.pan": IconPan,
  "panel.toggle.layers": IconLayers,
  "zones.generate": IconZone,
  "zones.rebuild": IconZone,
  "edit.undo": IconUndo,
  "edit.redo": IconUndo,
  "review.mode": IconValidate,
  "review.overlay": IconPolygon,
};

export function CommandIcon({
  command,
  size = 18,
  className,
}: {
  command: StudioCommandId;
  size?: number;
  className?: string;
}) {
  const Icon = COMMAND_ICONS[command] ?? IconPolygon;
  return <Icon size={size} className={className} />;
}
