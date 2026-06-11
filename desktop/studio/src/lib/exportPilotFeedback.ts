/** Open (Tauri) or download (browser) the pilot feedback template — no telemetry. */
export async function exportPilotFeedbackTemplate(): Promise<"open" | "download"> {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("open_pilot_feedback_template");
    return "open";
  } catch {
    /* not in Tauri or template missing on disk — download bundled copy */
  }

  const res = await fetch("/PILOT_FEEDBACK.md");
  if (!res.ok) {
    throw new Error("Could not load pilot feedback template");
  }
  const content = await res.text();
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "PILOT_FEEDBACK.md";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  return "download";
}
