import { useWorkspaceStore } from "../../stores/workspaceStore";

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function ActionLog() {
  const actions = useWorkspaceStore((s) => s.actions);

  return (
    <div className="border-t border-[var(--border-default)] p-2">
      <div className="mb-1 text-[10px] font-semibold text-[var(--text-secondary)]">
        Audit Log
      </div>
      <ul className="max-h-24 space-y-1 overflow-y-auto text-[10px]">
        {actions.slice(0, 8).map((a, i) => (
          <li
            key={`${a.at}-${i}`}
            className={`flex justify-between gap-2 ${
              a.kind === "success"
                ? "text-[var(--status-pass)]"
                : a.kind === "warn"
                  ? "text-[var(--status-review)]"
                  : ""
            }`}
          >
            <span className="truncate">
              {a.user ? `[${a.user}] ` : ""}
              {a.message}
            </span>
            <span className="shrink-0 text-[var(--text-muted)]">
              {formatTime(a.at)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
