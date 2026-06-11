import { useCallback, useEffect, useRef } from "react";
import { loadProjectFile, uploadDrawing } from "../../api/engine";
import { refreshScene, useStudioCommands } from "../../hooks/useStudioCommands";
import { applyProjectLoad } from "../../lib/applyProjectLoad";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { StudioCommandId } from "../../types";
import { Logo } from "../brand/Logo";
import { CommandPalette } from "../shell/CommandPalette";
import { GoToModal } from "../shell/GoToModal";
import { MenuBar } from "../shell/MenuBar";
import { RibbonBar } from "../shell/RibbonBar";
import { StudioToast } from "../shell/StudioToast";
import { ExportModal } from "../shell/ExportModal";
import { ExportSuccessPanel } from "../shell/ExportSuccessPanel";
import { LayerManagerModal } from "../shell/LayerManagerModal";
import { ReviewModePanel } from "../shell/ReviewModePanel";
import { ReviewOnlyBanner } from "../shell/ReviewOnlyBanner";
import { SaveWorkspaceModal } from "../shell/SaveWorkspaceModal";
import { EngineErrorBar } from "../shell/EngineErrorBar";
import { StatPills } from "../shell/StatPills";
import { ResizableWorkspace } from "./ResizableWorkspace";

function dispatchFitView() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.dispatchEvent(new CustomEvent("studio:fit-view"));
    });
  });
}

export function WorkspaceScreen() {
  const cadFileRef = useRef<HTMLInputElement>(null);
  const projectFileRef = useRef<HTMLInputElement>(null);
  const importAcceptRef = useRef<string>(".dxf,.dwg,.DXF,.DWG");

  const sourceFile = useWorkspaceStore((s) => s.sourceFile);
  const activeMenuTab = useWorkspaceStore((s) => s.activeMenuTab);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const workspaceSavePath = useWorkspaceStore((s) => s.workspaceSavePath);
  const setExportOpen = useWorkspaceStore((s) => s.setExportOpen);
  const setSettingsOpen = useWorkspaceStore((s) => s.setSettingsOpen);
  const setScene = useWorkspaceStore((s) => s.setScene);
  const setCounts = useWorkspaceStore((s) => s.setCounts);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setSourceFile = useWorkspaceStore((s) => s.setSourceFile);
  const setUnitLabel = useWorkspaceStore((s) => s.setUnitLabel);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const setValidation = useWorkspaceStore((s) => s.setValidation);
  const setZones = useWorkspaceStore((s) => s.setZones);
  const setWorkspaceSavePath = useWorkspaceStore((s) => s.setWorkspaceSavePath);
  const setCadAvailable = useWorkspaceStore((s) => s.setCadAvailable);
  const setSaveWorkspaceOpen = useWorkspaceStore((s) => s.setSaveWorkspaceOpen);

  const openImport = useCallback((format?: "dxf" | "dwg" | "any") => {
    if (format === "dxf") importAcceptRef.current = ".dxf,.DXF";
    else if (format === "dwg") importAcceptRef.current = ".dwg,.DWG";
    else importAcceptRef.current = ".dxf,.dwg,.DXF,.DWG";
    if (cadFileRef.current) {
      cadFileRef.current.accept = importAcceptRef.current;
      cadFileRef.current.click();
    }
  }, []);

  const openProject = useCallback(() => projectFileRef.current?.click(), []);

  const onRefresh = useCallback(async () => {
    try {
      await refreshScene();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Refresh failed");
    }
  }, [setEngineError]);

  const { executeCommand } = useStudioCommands({
    onOpenProject: openProject,
    onImportDrawing: openImport,
    onRefresh,
  });

  const onExecute = useCallback(
    (command: StudioCommandId) => {
      void executeCommand(command);
    },
    [executeCommand],
  );

  useEffect(() => {
    const onOpenFile = () => openImport("any");
    const onOpenProject = () => openProject();
    window.addEventListener("studio:open-file", onOpenFile);
    window.addEventListener("studio:open-project", onOpenProject);
    return () => {
      window.removeEventListener("studio:open-file", onOpenFile);
      window.removeEventListener("studio:open-project", onOpenProject);
    };
  }, [openImport, openProject]);

  const onCadFile = async (file: File) => {
    try {
      const data = await uploadDrawing(sessionId, file);
      setScene(data.scene);
      setCounts(data.counts);
      setActions(data.actions);
      setSourceFile(data.source_file);
      setUnitLabel(data.unit_label || "mm");
      useWorkspaceStore.getState().setExpectedPolygonCount(data.counts.total);
      setZones([]);
      setValidation(null);
      setWorkspaceSavePath(null);
      setCadAvailable(true);
      dispatchFitView();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Upload failed");
    }
  };

  const onProjectFile = async (file: File) => {
    try {
      const data = await loadProjectFile(sessionId, file);
      setScene(data.scene);
      setCounts(data.counts);
      setActions(data.actions);
      setSourceFile(data.source_file);
      setUnitLabel(data.unit_label || "mm");
      setValidation(data.validation);
      setZones(data.zones);
      setWorkspaceSavePath(data.workspace_save_path);
      setCadAvailable(data.cad_available);
      applyProjectLoad(data);
      dispatchFitView();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Open project failed");
    }
  };

  const onSaveClick = () => {
    const s = useWorkspaceStore.getState();
    if (!s.scene) return;
    if (s.workspaceSavePath) {
      void executeCommand("file.save");
    } else {
      setSaveWorkspaceOpen(true, false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <Logo size={24} className="text-[var(--brand-primary)]" />
          <div className="app-title">INT ZONE STUDIO</div>
        </div>
        {sourceFile && (
          <span className="file-pill mx-3 truncate">{sourceFile}</span>
        )}
        {workspaceSavePath && (
          <span className="file-pill mx-1 max-w-[200px] truncate text-[10px] opacity-80">
            {workspaceSavePath}
          </span>
        )}
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            className="btn-ghost text-xs"
            onClick={() => setSettingsOpen(true)}
          >
            Settings
          </button>
          <button
            type="button"
            className="btn-ghost text-xs"
            onClick={() => setExportOpen(true)}
          >
            Export
          </button>
          <button type="button" className="btn-primary text-xs" onClick={onSaveClick}>
            Save
          </button>
        </div>
      </header>

      <MenuBar onExecute={onExecute} />
      <RibbonBar onExecute={onExecute} />
      {activeMenuTab === "Detection" && <StatPills />}
      <ReviewOnlyBanner />
      <ReviewModePanel />

      <EngineErrorBar />

      <ResizableWorkspace />

      <StudioToast />

      <input
        ref={cadFileRef}
        type="file"
        accept=".dxf,.dwg,.DXF,.DWG"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onCadFile(f);
          e.target.value = "";
        }}
      />

      <input
        ref={projectFileRef}
        type="file"
        accept=".pjson,.json"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onProjectFile(f);
          e.target.value = "";
        }}
      />

      <ExportModal />
      <ExportSuccessPanel />
      <SaveWorkspaceModal />
      <LayerManagerModal />
      <CommandPalette onExecute={onExecute} />
      <GoToModal />
    </div>
  );
}
