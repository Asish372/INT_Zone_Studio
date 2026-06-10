import { useCallback, useEffect, useState } from "react";
import { ensureSession, waitForEngine } from "./api/engine";
import { ThemeProvider } from "./hooks/useTheme";
import { refreshScene, useStudioCommands } from "./hooks/useStudioCommands";
import { useStudioKeyboard } from "./hooks/useStudioKeyboard";
import { useWorkspaceStore } from "./stores/workspaceStore";
import { WelcomeScreen } from "./components/welcome/WelcomeScreen";
import { WorkspaceScreen } from "./components/workspace/WorkspaceScreen";
import { SettingsModal } from "./components/shell/SettingsModal";

function AppContent() {
  const screen = useWorkspaceStore((s) => s.screen);
  const setSessionId = useWorkspaceStore((s) => s.setSessionId);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const [ready, setReady] = useState(false);

  const { executeCommand } = useStudioCommands({
    onOpenProject: () => window.dispatchEvent(new CustomEvent("studio:open-project")),
    onImportDrawing: () => window.dispatchEvent(new CustomEvent("studio:open-file")),
    onRefresh: refreshScene,
  });

  const runCommand = useCallback(
    (command: Parameters<typeof executeCommand>[0]) => {
      void executeCommand(command);
    },
    [executeCommand],
  );

  useStudioKeyboard(runCommand);

  useEffect(() => {
    void (async () => {
      try {
        await waitForEngine();
        const id = await ensureSession();
        setSessionId(id);
        setReady(true);
      } catch (e) {
        setEngineError(e instanceof Error ? e.message : "Engine unavailable");
        setReady(true);
      }
    })();
  }, [setSessionId, setEngineError]);

  if (!ready) {
    return (
      <div className="flex h-full items-center justify-center text-[var(--text-secondary)]">
        Connecting to detection engine…
      </div>
    );
  }

  return (
    <>
      {screen === "workspace" ? <WorkspaceScreen /> : <WelcomeScreen />}
      <SettingsModal />
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
