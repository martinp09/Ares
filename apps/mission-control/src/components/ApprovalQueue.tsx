import type { ApprovalItem } from "../lib/api";

interface ApprovalQueueProps {
  approvals: ApprovalItem[];
}

export function ApprovalQueue({ approvals }: ApprovalQueueProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Approvals queue</h3>
        <span>{approvals.length} pending</span>
      </div>
      <div className="list-stack">
        {approvals.map((approval) => (
          <article className="list-card" key={approval.id}>
            <div className="list-card__row">
              <strong>{approval.title}</strong>
              <span className={`risk-pill risk-pill--${approval.riskLevel}`}>{approval.riskLevel}</span>
            </div>
            <p className="list-card__body">{approval.reason}</p>
            <p className="list-card__body list-card__body--muted">{approval.payloadPreview}</p>
            <div className="list-card__row list-card__row--muted">
              <span>{approval.commandType}</span>
              <span>{approval.requestedAt}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
