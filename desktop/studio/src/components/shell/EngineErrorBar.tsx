import { useWorkspaceStore } from "../../stores/workspaceStore";

export function EngineErrorBar() {
  const engineError = useWorkspaceStore((s) => s.engineError);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);

  if (!engineError) return null;

  return (
    <div className="engine-error-bar">
      {engineError}
      <button
        type="button"
        className="ml-2 underline"
        onClick={() => setEngineError(null)}
      >
        dismiss
      </button>
    </div>
  );
}
