import type { GovernanceData } from "../lib/api";

interface AuditTimelineProps {
  events: GovernanceData["recentAudit"];
}

export function AuditTimeline({ events }: AuditTimelineProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Recent audit</h3>
        <span>{events.length} events</span>
      </div>
      {events.length > 0 ? (
        <div className="list-stack">
          {events.map((event) => (
            <article className="list-card" key={event.id}>
              <div className="list-card__row">
                <strong>{event.summary}</strong>
                <span>{event.eventType}</span>
              </div>
              <p className="list-card__body list-card__body--muted">{event.createdAt}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="list-card__body list-card__body--muted">No audit events are currently available.</p>
      )}
    </section>
  );
}
