import type { RunSummary } from "../lib/api";

interface RunTimelineProps {
  runs: RunSummary[];
}

export function RunTimeline({ runs }: RunTimelineProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Runs timeline</h3>
        <span>{runs.length} visible</span>
      </div>
      <div className="list-stack">
        {runs.map((run) => (
          <article className="list-card" key={run.id}>
            <div className="list-card__row">
              <strong>{run.commandType}</strong>
              <span className={`status-pill status-pill--${run.status}`}>{run.status}</span>
            </div>
            <p className="list-card__body">{run.summary}</p>
            <div className="list-card__row list-card__row--muted">
              <span>{run.id}</span>
              <span>{run.updatedAt}</span>
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>{run.businessId} / {run.environment}</span>
              <span>{run.parentRunId ? `parent ${run.parentRunId}` : "root run"}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
