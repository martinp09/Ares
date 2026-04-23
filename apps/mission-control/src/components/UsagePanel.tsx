import type { GovernanceData } from "../lib/api";

interface UsagePanelProps {
  usageSummary: GovernanceData["usageSummary"];
  recentUsage: GovernanceData["recentUsage"];
}

export function UsagePanel({ usageSummary, recentUsage }: UsagePanelProps) {
  const usageByKind = Object.entries(usageSummary.byKind)
    .map(([kind, count]) => `${kind}: ${count}`)
    .join(" • ");

  return (
    <>
      <section className="panel-stack" aria-label="Usage summary">
        <div className="list-stack">
          <article className="list-card">
            <div className="list-card__row">
              <strong>Usage summary</strong>
              <span>{usageSummary.totalCount} events</span>
            </div>
            <p className="list-card__body list-card__body--muted">{usageByKind || "No usage recorded."}</p>
          </article>
        </div>
      </section>

      <section className="panel-stack" aria-label="Recent usage">
        <div className="section-heading">
          <h3>Recent usage</h3>
          <span>{recentUsage.length} entries</span>
        </div>
        <div className="list-stack">
          {recentUsage.length > 0 ? (
            recentUsage.map((event) => (
              <article className="list-card" key={event.id}>
                <div className="list-card__row">
                  <strong>{event.kind}</strong>
                  <span>{event.count}</span>
                </div>
                <p className="list-card__body list-card__body--muted">
                  {[event.sourceKind, event.createdAt].filter(Boolean).join(" • ")}
                </p>
              </article>
            ))
          ) : (
            <article className="list-card">
              <div className="list-card__row">
                <strong>No recent usage</strong>
                <span>0 entries</span>
              </div>
              <p className="list-card__body list-card__body--muted">No usage recorded.</p>
            </article>
          )}
        </div>
      </section>
    </>
  );
}
