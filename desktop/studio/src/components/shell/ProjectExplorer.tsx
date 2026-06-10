import { useEffect, useState } from "react";
import {
  createProject,
  fetchProjects,
  generateZones,
  loadProjectVersion,
  saveProjectVersion,
} from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";

export function ProjectExplorer() {
  const sourceFile = useWorkspaceStore((s) => s.sourceFile);
  const counts = useWorkspaceStore((s) => s.counts);
  const layers = useWorkspaceStore((s) => s.layers);
  const zones = useWorkspaceStore((s) => s.zones);
  const projects = useWorkspaceStore((s) => s.projects);
  const activeProjectId = useWorkspaceStore((s) => s.activeProjectId);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const setLayers = useWorkspaceStore((s) => s.setLayers);
  const setZones = useWorkspaceStore((s) => s.setZones);
  const setScene = useWorkspaceStore((s) => s.setScene);
  const setCounts = useWorkspaceStore((s) => s.setCounts);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setProjects = useWorkspaceStore((s) => s.setProjects);
  const setActiveProjectId = useWorkspaceStore((s) => s.setActiveProjectId);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);

  const [open, setOpen] = useState({
    project: true,
    drawing: true,
    layers: true,
    polygons: true,
    intZones: true,
    versions: false,
  });

  const toggle = (key: keyof typeof open) =>
    setOpen((o) => ({ ...o, [key]: !o[key] }));

  useEffect(() => {
    void fetchProjects()
      .then(setProjects)
      .catch(() => {});
  }, [setProjects]);

  const activeProject = projects.find((p) => p.id === activeProjectId);

  const onGenerateZones = async () => {
    try {
      const data = await generateZones(sessionId);
      setZones(data.zones);
      setScene(data.scene);
      setActions(data.actions);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Zone generation failed");
    }
  };

  const onCreateProject = async () => {
    const name = prompt("Project name:", "Warehouse Project");
    if (!name) return;
    try {
      const p = await createProject(name);
      setProjects([...projects, p]);
      setActiveProjectId(p.id);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Create project failed");
    }
  };

  const onSaveVersion = async () => {
    if (!activeProjectId) {
      await onCreateProject();
      return;
    }
    try {
      const p = await saveProjectVersion(sessionId, activeProjectId);
      setProjects(projects.map((x) => (x.id === p.id ? p : x)));
      setActions([
        { message: `Version ${p.current_version} saved`, kind: "success", at: new Date().toISOString() },
        ...useWorkspaceStore.getState().actions,
      ]);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Save version failed");
    }
  };

  const onLoadVersion = async (versionId: string) => {
    if (!activeProjectId) return;
    try {
      const data = await loadProjectVersion(sessionId, activeProjectId, versionId);
      setScene(data.scene);
      setCounts(data.counts);
      setActions(data.actions);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Load version failed");
    }
  };

  return (
    <aside className="flex h-full min-h-0 flex-col overflow-y-auto bg-[var(--surface-panel)] text-xs">
      <div className="border-b border-[var(--border-default)] px-3 py-2 font-semibold text-[var(--text-secondary)]">
        Project Explorer
      </div>

      <div className="p-2">
        <button type="button" className="tree-node w-full text-left font-medium" onClick={() => toggle("project")}>
          {open.project ? "▼" : "▶"} {activeProject?.name ?? "Projects"}
        </button>
        {open.project && (
          <div className="ml-3 mt-1 space-y-1">
            <button type="button" className="text-[var(--brand-primary)] hover:underline" onClick={() => void onCreateProject()}>
              + New Project
            </button>
            {projects.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`block w-full text-left ${p.id === activeProjectId ? "font-semibold text-[var(--brand-primary)]" : ""}`}
                onClick={() => setActiveProjectId(p.id)}
              >
                {p.name}
              </button>
            ))}
            {activeProject && (
              <>
                <button type="button" className="mt-1 text-[var(--brand-primary)] hover:underline" onClick={() => void onSaveVersion()}>
                  Save Version
                </button>
                <button type="button" className="tree-node mt-2 w-full text-left" onClick={() => toggle("versions")}>
                  {open.versions ? "▼" : "▶"} Versions ({activeProject.versions.length})
                </button>
                {open.versions &&
                  activeProject.versions.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      className="ml-2 block text-left text-[var(--text-secondary)] hover:text-[var(--brand-primary)]"
                      onClick={() => void onLoadVersion(v.id)}
                    >
                      {v.label} — {v.polygon_count} polys
                    </button>
                  ))}
              </>
            )}
          </div>
        )}

        <button type="button" className="tree-node mt-2 w-full text-left font-medium" onClick={() => toggle("drawing")}>
          {open.drawing ? "▼" : "▶"} Drawing
        </button>
        {open.drawing && (
          <div className="ml-3 mt-1 text-[var(--text-secondary)]">{sourceFile || "—"}</div>
        )}

        <button type="button" className="tree-node mt-2 w-full text-left font-medium" onClick={() => toggle("layers")}>
          {open.layers ? "▼" : "▶"} Layers
        </button>
        {open.layers && (
          <div className="ml-3 mt-1 space-y-1">
            {(
              [
                ["cad", "CAD Lines"],
                ["auto", "Detected Polygons"],
                ["seed", "Recovered Polygons"],
                ["deleted", "Deleted"],
                ["labels", "Polygon Labels"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={layers[key]}
                  onChange={(e) => setLayers({ [key]: e.target.checked })}
                />
                {label}
              </label>
            ))}
          </div>
        )}

        <button type="button" className="tree-node mt-2 w-full text-left font-medium" onClick={() => toggle("polygons")}>
          {open.polygons ? "▼" : "▶"} Polygons
        </button>
        {open.polygons && (
          <div className="ml-3 mt-1 space-y-0.5 text-[var(--text-secondary)]">
            <div>Auto Detected ({counts.detected})</div>
            <div>Seed Recovered ({counts.seed_added})</div>
            <div>Deleted ({counts.deleted})</div>
          </div>
        )}

        <button type="button" className="tree-node mt-2 w-full text-left font-medium" onClick={() => toggle("intZones")}>
          {open.intZones ? "▼" : "▶"} INT Zones ({zones.length || "—"})
        </button>
        {open.intZones && (
          <div className="ml-3 mt-1 space-y-1">
            <button type="button" className="text-[var(--brand-primary)] hover:underline" onClick={() => void onGenerateZones()}>
              Auto Group Polygons
            </button>
            {zones.map((z) => (
              <div key={z.label} className="text-[var(--text-secondary)]">
                <strong>{z.label}</strong> — {z.area_m2.toFixed(0)} m², {z.face_count} faces
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
