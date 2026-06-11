import { commitManualPolygon } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";

export function ManualPolygonBanner() {
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const manualPolygonPreview = useWorkspaceStore((s) => s.manualPolygonPreview);
  const setManualPolygonPreview = useWorkspaceStore((s) => s.setManualPolygonPreview);
  const setScene = useWorkspaceStore((s) => s.setScene);
  const setCounts = useWorkspaceStore((s) => s.setCounts);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setSelected = useWorkspaceStore((s) => s.setSelected);
  const setTool = useWorkspaceStore((s) => s.setTool);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const clearManualDraw = useWorkspaceStore((s) => s.clearManualDraw);

  if (!manualPolygonPreview) return null;

  const onCancel = () => {
    clearManualDraw();
    setTool("select");
  };

  const onConfirm = async () => {
    try {
      const data = await commitManualPolygon(sessionId, manualPolygonPreview.ring);
      setScene(data.scene);
      setCounts(data.counts);
      setActions(data.actions);
      setSelected(data.polygon.id, data.polygon);
      clearManualDraw();
      setManualPolygonPreview(null);
      setTool("select");
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Could not add manual polygon");
    }
  };

  return (
    <div className="seed-banner absolute left-1/2 top-12 z-20 -translate-x-1/2 px-4 py-2 text-sm shadow-lg">
      Manual polygon preview — {manualPolygonPreview.area_m2.toFixed(2)} m² —{" "}
      <button type="button" className="underline" onClick={() => void onConfirm()}>
        Confirm
      </button>
      {" · "}
      <button type="button" className="underline" onClick={onCancel}>
        Cancel
      </button>
    </div>
  );
}
