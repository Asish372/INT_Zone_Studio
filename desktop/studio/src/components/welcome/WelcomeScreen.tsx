import { useEffect, useRef, useState } from "react";
import { ensureSession, loadProjectFile, uploadDrawing } from "../../api/engine";
import { applyProjectLoad } from "../../lib/applyProjectLoad";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import { BUILD_LABEL, PRODUCT_NAME } from "../../lib/buildInfo";
import { Logo } from "../brand/Logo";

function dispatchFitView() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.dispatchEvent(new CustomEvent("studio:fit-view"));
    });
  });
}

export function WelcomeScreen() {
  const cadInputRef = useRef<HTMLInputElement>(null);
  const projectInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const setScreen = useWorkspaceStore((s) => s.setScreen);
  const setSessionId = useWorkspaceStore((s) => s.setSessionId);
  const setScene = useWorkspaceStore((s) => s.setScene);
  const setCounts = useWorkspaceStore((s) => s.setCounts);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setSourceFile = useWorkspaceStore((s) => s.setSourceFile);
  const setUnitLabel = useWorkspaceStore((s) => s.setUnitLabel);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const setSettingsOpen = useWorkspaceStore((s) => s.setSettingsOpen);
  const setValidation = useWorkspaceStore((s) => s.setValidation);
  const setZones = useWorkspaceStore((s) => s.setZones);
  const setWorkspaceSavePath = useWorkspaceStore((s) => s.setWorkspaceSavePath);
  const setCadAvailable = useWorkspaceStore((s) => s.setCadAvailable);

  const handleCadFile = async (file: File) => {
    setLoading(true);
    setEngineError(null);
    try {
      const sessionId = await ensureSession();
      const data = await uploadDrawing(sessionId, file);
      setSessionId(data.session_id || sessionId);
      setScene(data.scene);
      setCounts(data.counts);
      setActions(data.actions);
      setSourceFile(data.source_file);
      setUnitLabel(data.unit_label || "mm");
      setZones([]);
      setValidation(null);
      setWorkspaceSavePath(null);
      setCadAvailable(true);
      setScreen("workspace");
      dispatchFitView();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const onOpenProject = () => projectInputRef.current?.click();
    const onImport = () => cadInputRef.current?.click();
    window.addEventListener("studio:open-project", onOpenProject);
    window.addEventListener("studio:open-file", onImport);
    return () => {
      window.removeEventListener("studio:open-project", onOpenProject);
      window.removeEventListener("studio:open-file", onImport);
    };
  }, []);

  const handleProjectFile = async (file: File) => {
    setLoading(true);
    setEngineError(null);
    try {
      const sessionId = await ensureSession();
      const data = await loadProjectFile(sessionId, file);
      setSessionId(data.session_id || sessionId);
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
      setScreen("workspace");
      dispatchFitView();
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Open project failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      <aside className="flex w-52 flex-col gap-3 border-r border-[var(--border-default)] bg-[var(--surface-panel)] p-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 font-bold text-[var(--brand-primary)]">
            <Logo size={24} />
            <span className="text-sm tracking-wide">{PRODUCT_NAME.toUpperCase()}</span>
          </div>
          <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-secondary)]">
            {BUILD_LABEL}
          </span>
        </div>
        <button
          type="button"
          className="btn-primary w-full"
          onClick={() => projectInputRef.current?.click()}
          disabled={loading}
        >
          Open Project
        </button>
        <button
          type="button"
          className="btn-ghost w-full"
          onClick={() => cadInputRef.current?.click()}
          disabled={loading}
        >
          Import Drawing
        </button>
        <input
          ref={projectInputRef}
          type="file"
          accept=".pjson,.json"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleProjectFile(f);
            e.target.value = "";
          }}
        />
        <input
          ref={cadInputRef}
          type="file"
          accept=".dxf,.dwg,.DXF,.DWG"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleCadFile(f);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="btn-ghost w-full text-sm"
          onClick={() => setSettingsOpen(true)}
        >
          Settings
        </button>
      </aside>

      <main className="flex flex-1 flex-col items-center justify-center bg-[var(--surface-deep)] p-8">
        <div
          className={`drop-zone w-full max-w-lg ${dragging ? "drop-zone-active" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const f = e.dataTransfer.files?.[0];
            if (!f) return;
            const ext = f.name.split(".").pop()?.toLowerCase();
            if (ext === "pjson" || ext === "json") void handleProjectFile(f);
            else void handleCadFile(f);
          }}
        >
          <h2 className="text-lg font-semibold">Get started</h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Open a saved workspace (.pjson) or import a DXF/DWG drawing to begin detection.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <button
              type="button"
              className="btn-primary"
              onClick={() => projectInputRef.current?.click()}
              disabled={loading}
            >
              {loading ? "Loading…" : "Open Project"}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => cadInputRef.current?.click()}
              disabled={loading}
            >
              Import Drawing
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
