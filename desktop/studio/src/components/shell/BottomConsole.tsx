import { useMemo, useState } from "react";
import { useWorkspaceStore } from "../../stores/workspaceStore";

const TABS = ["Messages", "Detection Log", "Validation", "Exports"] as const;
type ConsoleTab = (typeof TABS)[number];

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

export function BottomConsole() {
  const [activeTab, setActiveTab] = useState<ConsoleTab>("Messages");
  const actions = useWorkspaceStore((s) => s.actions);
  const validation = useWorkspaceStore((s) => s.validation);
  const counts = useWorkspaceStore((s) => s.counts);

  const detectionLog = useMemo(
    () =>
      actions.filter((a) =>
        /detect|recover|seed|gap|polygon|zone|validat/i.test(a.message),
      ),
    [actions],
  );

  const exportLog = useMemo(
    () => actions.filter((a) => /export|saved|package|dxf|excel|csv|pdf/i.test(a.message)),
    [actions],
  );

  const renderBody = () => {
    if (activeTab === "Messages") {
      if (!actions.length) {
        return <div className="console-line console-line-muted">No messages yet.</div>;
      }
      return actions.slice(0, 50).map((a, i) => (
        <div
          key={`${a.at}-${i}`}
          className={`console-line ${
            a.kind === "success"
              ? "console-line-success"
              : a.kind === "warn"
                ? "console-line-warn"
                : ""
          }`}
        >
          <span className="console-time">{formatTime(a.at)}</span>
          <span className="console-msg">{a.message}</span>
        </div>
      ));
    }

    if (activeTab === "Detection Log") {
      if (!detectionLog.length) {
        return (
          <div className="console-line console-line-muted">
            Detection events appear here after run, recovery, or validation.
          </div>
        );
      }
      return detectionLog.slice(0, 50).map((a, i) => (
        <div key={`${a.at}-${i}`} className="console-line">
          <span className="console-time">{formatTime(a.at)}</span>
          <span className="console-msg">{a.message}</span>
        </div>
      ));
    }

    if (activeTab === "Validation") {
      if (!validation) {
        return (
          <div className="console-line console-line-muted">
            Run validation to see results. Detected: {counts.detected} · Total: {counts.total}
          </div>
        );
      }
      const issues = validation.issues ?? [];
      if (!issues.length) {
        return <div className="console-line console-line-success">No validation issues.</div>;
      }
      return issues.map((issue, i) => (
        <div
          key={`${issue.type}-${i}`}
          className={`console-line ${
            issue.severity === "error" ? "console-line-error" : "console-line-warn"
          }`}
        >
          <span className="console-time">{issue.severity}</span>
          <span className="console-msg">{issue.message}</span>
        </div>
      ));
    }

    if (!exportLog.length) {
      return (
        <div className="console-line console-line-muted">
          Export activity will be logged here.
        </div>
      );
    }
    return exportLog.slice(0, 50).map((a, i) => (
      <div key={`${a.at}-${i}`} className="console-line console-line-success">
        <span className="console-time">{formatTime(a.at)}</span>
        <span className="console-msg">{a.message}</span>
      </div>
    ));
  };

  return (
    <div className="bottom-console">
      <div className="bottom-console-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            className={`console-tab ${tab === activeTab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="bottom-console-body">{renderBody()}</div>
    </div>
  );
}
