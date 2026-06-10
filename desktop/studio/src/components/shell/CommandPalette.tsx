import { useEffect, useMemo, useRef, useState } from "react";
import { COMMAND_CATALOG } from "../../shell/commandCatalog";
import { MENU_DEFINITIONS } from "../../shell/menuConfig";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { StudioCommandId } from "../../types";

interface CommandPaletteProps {
  onExecute: (command: StudioCommandId) => void;
}

function buildAllCommands() {
  const fromMenus = MENU_DEFINITIONS.flatMap((menu) =>
    menu.groups.flatMap((g) =>
      g.items
        .filter((i) => i.command)
        .map((i) => ({
          id: i.command!,
          label: i.label,
          category: menu.tab,
          shortcut: i.shortcut,
        })),
    ),
  );
  const seen = new Set<string>();
  const merged = [...COMMAND_CATALOG, ...fromMenus].filter((c) => {
    if (seen.has(c.id)) return false;
    seen.add(c.id);
    return true;
  });
  return merged;
}

const ALL_COMMANDS = buildAllCommands();

export function CommandPalette({ onExecute }: CommandPaletteProps) {
  const open = useWorkspaceStore((s) => s.commandPaletteOpen);
  const setOpen = useWorkspaceStore((s) => s.setCommandPaletteOpen);
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return ALL_COMMANDS.slice(0, 16);
    return ALL_COMMANDS.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q) ||
        ("keywords" in c && c.keywords?.some((k: string) => k.includes(q))),
    ).slice(0, 20);
  }, [query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setIndex(0);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    setIndex(0);
  }, [query]);

  if (!open) return null;

  const run = (cmd: StudioCommandId) => {
    setOpen(false);
    onExecute(cmd);
  };

  return (
    <div
      className="modal-overlay command-palette-overlay"
      onClick={() => setOpen(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape") setOpen(false);
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setIndex((i) => Math.min(i + 1, results.length - 1));
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setIndex((i) => Math.max(i - 1, 0));
        }
        if (e.key === "Enter" && results[index]) {
          e.preventDefault();
          run(results[index].id);
        }
      }}
    >
      <div
        className="command-palette"
        role="dialog"
        aria-label="Command Palette"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="command-palette-input"
          placeholder="Type a command… (e.g. Generate Zones, Export DXF)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <ul className="command-palette-list">
          {results.map((cmd, i) => (
            <li key={cmd.id}>
              <button
                type="button"
                className={`command-palette-item ${i === index ? "command-palette-item-active" : ""}`}
                onMouseEnter={() => setIndex(i)}
                onClick={() => run(cmd.id)}
              >
                <span className="command-palette-label">{cmd.label}</span>
                <span className="command-palette-meta">
                  {cmd.shortcut && <span>{cmd.shortcut}</span>}
                  <span>{cmd.category}</span>
                </span>
              </button>
            </li>
          ))}
          {results.length === 0 && (
            <li className="command-palette-empty">No matching commands</li>
          )}
        </ul>
      </div>
    </div>
  );
}
