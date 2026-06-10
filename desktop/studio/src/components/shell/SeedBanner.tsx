import { useWorkspaceStore } from "../../stores/workspaceStore";

export function SeedBanner() {
  const tool = useWorkspaceStore((s) => s.tool);
  const setTool = useWorkspaceStore((s) => s.setTool);
  const setSeedPreview = useWorkspaceStore((s) => s.setSeedPreview);

  if (tool !== "add") return null;

  return (
    <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
      Seed Recovery Mode: Click inside the missing polygon area —{" "}
      <button
        type="button"
        className="underline"
        onClick={() => {
          setSeedPreview(null, null);
          setTool("select");
        }}
      >
        Esc to cancel
      </button>
    </div>
  );
}
