import { useWorkspaceStore } from "../../stores/workspaceStore";

export function StudioToast() {
  const message = useWorkspaceStore((s) => s.studioToast);
  if (!message) return null;
  return <div className="studio-toast">{message}</div>;
}
