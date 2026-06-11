import { useState } from "react";
import { confirmSeedRecovery } from "../viewer/CadCanvas";
import { reviewPolygon, addComment } from "../../api/engine";
import { useWorkspaceStore } from "../../stores/workspaceStore";
import type { ReviewStatus } from "../../types";

export function PropertiesPanel() {
  const selectedPolygon = useWorkspaceStore((s) => s.selectedPolygon);
  const seedPreview = useWorkspaceStore((s) => s.seedPreview);
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const showVertices = useWorkspaceStore((s) => s.showVertices);
  const comments = useWorkspaceStore((s) => s.comments);
  const setSeedPreview = useWorkspaceStore((s) => s.setSeedPreview);
  const setEngineError = useWorkspaceStore((s) => s.setEngineError);
  const setScene = useWorkspaceStore((s) => s.setScene);
  const setActions = useWorkspaceStore((s) => s.setActions);
  const setSelected = useWorkspaceStore((s) => s.setSelected);
  const setShowVertices = useWorkspaceStore((s) => s.setShowVertices);
  const setComments = useWorkspaceStore((s) => s.setComments);
  const [commentText, setCommentText] = useState("");

  const handleReview = async (status: ReviewStatus) => {
    if (!selectedPolygon) return;
    try {
      const data = await reviewPolygon(sessionId, selectedPolygon.id, status);
      setScene(data.scene);
      setActions(data.actions);
      setSelected(data.polygon.id, data.polygon);
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Review failed");
    }
  };

  const handleAddComment = async () => {
    if (!selectedPolygon || !commentText.trim()) return;
    try {
      const c = await addComment(sessionId, selectedPolygon.id, commentText.trim());
      setComments(selectedPolygon.id, c);
      setCommentText("");
    } catch (e) {
      setEngineError(e instanceof Error ? e.message : "Comment failed");
    }
  };

  if (seedPreview) {
    return (
      <div className="flex min-h-0 flex-1 flex-col border-b border-[var(--border-default)] bg-[var(--surface-panel)] text-xs">
        <div className="border-b border-[var(--border-default)] px-3 py-2 font-semibold">
          Recovery Preview
        </div>
        <div className="space-y-2 p-3">
          <div className="info-row">
            <span className="label">Area</span>
            <span>{seedPreview.area_m2.toFixed(2)} m²</span>
          </div>
          <div className="info-row">
            <span className="label">Perimeter</span>
            <span>{seedPreview.perimeter_m.toFixed(2)} m</span>
          </div>
          <button
            type="button"
            className="btn-primary mt-4 w-full"
            onClick={() => {
              void confirmSeedRecovery().catch((e) =>
                setEngineError(e instanceof Error ? e.message : "Confirm failed"),
              );
            }}
          >
            Confirm Recovery
          </button>
          <button
            type="button"
            className="btn-ghost w-full"
            onClick={() => setSeedPreview(null, null)}
          >
            Cancel (Esc)
          </button>
        </div>
      </div>
    );
  }

  if (!selectedPolygon) {
    return (
      <div className="flex min-h-0 flex-1 flex-col border-b border-[var(--border-default)] bg-[var(--surface-panel)] text-xs">
        <div className="border-b border-[var(--border-default)] px-3 py-2 font-semibold">
          Polygon Inspector
        </div>
        <p className="p-3 text-[var(--text-muted)]">
          Select a polygon or use Seed Recovery
        </p>
      </div>
    );
  }

  const srcLabel =
    selectedPolygon.source === "seed"
      ? "Recovered"
      : selectedPolygon.source === "manual"
        ? "Manual"
        : "Auto";
  const polyComments = comments[selectedPolygon.id] ?? [];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto border-b border-[var(--border-default)] bg-[var(--surface-panel)] text-xs">
      <div className="border-b border-[var(--border-default)] px-3 py-2 font-semibold">
        Polygon #{selectedPolygon.id}
      </div>
      <div className="space-y-2 p-3">
        <div className="info-row">
          <span className="label">Source</span>
          <span
            className={
              selectedPolygon.source === "seed"
                ? "text-[var(--polygon-seed)]"
                : selectedPolygon.source === "manual"
                  ? "text-violet-400"
                  : ""
            }
          >
            {srcLabel}
          </span>
        </div>
        <div className="info-row">
          <span className="label">Layer</span>
          <span>{selectedPolygon.layer ?? "DETECTED_REGIONS"}</span>
        </div>
        <div className="info-row">
          <span className="label">Status</span>
          <span className="capitalize text-[var(--status-review)]">
            {selectedPolygon.review_status ?? "pending"}
          </span>
        </div>
        <div className="info-row">
          <span className="label">INT Zone</span>
          <span>{selectedPolygon.int_zone ?? "—"}</span>
        </div>
        <div className="info-row">
          <span className="label">Area</span>
          <span>{(selectedPolygon.area_m2 ?? 0).toFixed(2)} m²</span>
        </div>
        <div className="info-row">
          <span className="label">Perimeter</span>
          <span>{(selectedPolygon.perimeter_m ?? 0).toFixed(2)} m</span>
        </div>
        <div className="info-row">
          <span className="label">Vertices</span>
          <span>{selectedPolygon.ring?.length ?? 0}</span>
        </div>
        <div className="info-row">
          <span className="label">Centroid</span>
          <span>
            {selectedPolygon.centroid
              ? `${selectedPolygon.centroid[0].toFixed(1)}, ${selectedPolygon.centroid[1].toFixed(1)}`
              : "—"}
          </span>
        </div>
        <div className="info-row">
          <span className="label">Created By</span>
          <span>{selectedPolygon.created_by ?? "System"}</span>
        </div>

        <button
          type="button"
          className="btn-ghost mt-2 w-full"
          onClick={() => setShowVertices(!showVertices)}
        >
          {showVertices ? "Hide Vertices" : "View Vertices"}
        </button>

        {showVertices && selectedPolygon.ring && (
          <div className="max-h-24 overflow-auto rounded border border-[var(--border-default)] p-2 font-mono text-[10px]">
            {selectedPolygon.ring.map((v, i) => (
              <div key={i}>
                {i}: {v[0].toFixed(2)}, {v[1].toFixed(2)}
              </div>
            ))}
          </div>
        )}

        <div className="mt-3 border-t border-[var(--border-default)] pt-2">
          <div className="mb-1 font-semibold">Review</div>
          <div className="flex flex-wrap gap-1">
            <button type="button" className="btn-ghost px-2 py-0.5 text-[10px]" onClick={() => void handleReview("needs_review")}>
              Needs Review
            </button>
            <button type="button" className="btn-ghost px-2 py-0.5 text-[10px] text-green-600" onClick={() => void handleReview("approved")}>
              Approve
            </button>
            <button type="button" className="btn-ghost px-2 py-0.5 text-[10px] text-red-500" onClick={() => void handleReview("rejected")}>
              Reject
            </button>
          </div>
        </div>

        <div className="mt-2 border-t border-[var(--border-default)] pt-2">
          <div className="mb-1 font-semibold">Comments</div>
          {polyComments.map((c, i) => (
            <div key={i} className="mb-1 text-[10px] text-[var(--text-secondary)]">
              <strong>{c.user}:</strong> {c.text}
            </div>
          ))}
          <input
            className="mt-1 w-full rounded border border-[var(--border-default)] bg-transparent px-2 py-1 text-[10px]"
            placeholder="Add comment..."
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void handleAddComment()}
          />
        </div>
      </div>
    </div>
  );
}
