import { useEffect } from "react";
import { useWorkspaceStore } from "../stores/workspaceStore";
import type { StudioCommandId } from "../types";

export function useStudioKeyboard(
  executeCommand: (command: StudioCommandId) => void,
) {
  const screen = useWorkspaceStore((s) => s.screen);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (screen !== "workspace") return;
      const target = e.target;
      const inInput =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement;

      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "p") {
        e.preventDefault();
        executeCommand("palette.open");
        return;
      }

      if (inInput) return;

      if (e.ctrlKey && e.key.toLowerCase() === "g") {
        e.preventDefault();
        executeCommand("polygon.find");
        return;
      }
      if (e.ctrlKey && e.key.toLowerCase() === "z" && !e.shiftKey) {
        e.preventDefault();
        executeCommand("edit.undo");
        return;
      }
      if (e.ctrlKey && (e.key.toLowerCase() === "y" || (e.shiftKey && e.key.toLowerCase() === "z"))) {
        e.preventDefault();
        executeCommand("edit.redo");
        return;
      }
      if (e.ctrlKey && e.key.toLowerCase() === "s") {
        e.preventDefault();
        executeCommand("file.save");
        return;
      }
      if (e.ctrlKey && e.key.toLowerCase() === "o") {
        e.preventDefault();
        executeCommand("file.openProject");
        return;
      }

      if (e.key === "s" || e.key === "S") useWorkspaceStore.getState().setTool("select");
      if (e.key === "a" || e.key === "A") useWorkspaceStore.getState().setTool("add");
      if (e.key === "p" || e.key === "P") useWorkspaceStore.getState().setTool("pan");
      if (e.key === "f" || e.key === "F")
        window.dispatchEvent(new CustomEvent("studio:fit-view"));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [screen, executeCommand]);
}
