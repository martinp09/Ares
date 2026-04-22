import { RunTimeline } from "../components/RunTimeline";
import type { RunSummary } from "../lib/api";

interface RunsPageProps {
  runs: RunSummary[];
}

function summarizeReplay(run: RunSummary): string {
  const replay = run.replay;
  if (!replay) {
    return run.summary;
  }
  const lineage = [replay.source?.releaseEventType, replay.replay?.releaseEventType].filter(Boolean).join(" → ");
  if (replay.role === "child") {
    return `${replay.replayReason ?? "Replay child"} · parent ${replay.parentRunId ?? "unknown"} · ${lineage || "release context unavailable"}`;
  }
  if (replay.requiresApproval) {
    return `${replay.replayReason ?? "Replay requested"} · awaiting approval ${replay.approvalId ?? "pending"}`;
  }
  return `${replay.replayReason ?? "Replay requested"} · child ${replay.childRunId ?? "pending"} · ${lineage || "release context unavailable"}`;
}

export function RunsPage({ runs }: RunsPageProps) {
  const replayRuns = runs.filter((run) => run.replay);
  const replayParents = replayRuns.filter((run) => run.replay?.role === "parent").length;
  const replayChildren = replayRuns.filter((run) => run.replay?.role === "child").length;
  const replayAwaitingApproval = replayRuns.filter((run) => run.replay?.requiresApproval).length;

  return (
    <div className="page-stack">
      <section className="panel-stack">
        <div className="section-heading">
          <h3>Replay lineage</h3>
          <span>{replayRuns.length} runs with replay state</span>
        </div>
        <div className="summary-grid summary-grid--secondary">
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Replay parents</p>
            <strong className="summary-card__value">{replayParents}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Replay children</p>
            <strong className="summary-card__value">{replayChildren}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Awaiting approval</p>
            <strong className="summary-card__value">{replayAwaitingApproval}</strong>
          </article>
        </div>
        {replayRuns.length > 0 ? (
          <div className="list-stack">
            {replayRuns.map((run) => (
              <article className="list-card" key={`${run.id}-replay`}>
                <div className="list-card__row">
                  <strong>{run.commandType}</strong>
                  <span>{run.replay?.role}</span>
                </div>
                <p className="list-card__body">{summarizeReplay(run)}</p>
                <div className="list-card__row list-card__row--muted">
                  <span>{run.id}</span>
                  <span>{run.replay?.requestedAt ?? run.updatedAt}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="panel-copy">No replay lineage is visible for the current run scope yet.</p>
        )}
      </section>

      <RunTimeline runs={runs} />
    </div>
  );
}
