import { useTheme } from "../../hooks/useTheme";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { ThemeMode } from "../../types";

export function SettingsModal() {
  const open = useWorkspaceStore((s) => s.settingsOpen);
  const setSettingsOpen = useWorkspaceStore((s) => s.setSettingsOpen);
  const { mode, setMode } = useTheme();

  if (!open) return null;

  const options: { value: ThemeMode; label: string }[] = [
    { value: "system", label: "System" },
    { value: "light", label: "Light" },
    { value: "dark", label: "Dark" },
  ];

  return (
    <div className="modal-overlay">
      <div className="modal-card max-w-sm">
        <header className="modal-header">
          <h2 className="text-lg font-semibold">Settings</h2>
          <button
            type="button"
            className="text-xl"
            onClick={() => setSettingsOpen(false)}
          >
            ×
          </button>
        </header>
        <div className="p-4">
          <div className="mb-2 text-sm font-medium">Appearance</div>
          <div className="flex gap-2">
            {options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`btn-ghost flex-1 ${mode === opt.value ? "ring-2 ring-[var(--brand-primary)]" : ""}`}
                onClick={() => setMode(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <footer className="border-t border-[var(--border-default)] p-3">
          <button
            type="button"
            className="btn-primary"
            onClick={() => setSettingsOpen(false)}
          >
            Done
          </button>
        </footer>
      </div>
    </div>
  );
}
