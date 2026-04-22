import { ConnectLaterPanel } from "../components/ConnectLaterPanel";
import type { AssetSummary, GovernanceData } from "../lib/api";

interface SettingsPageProps {
  governance: GovernanceData;
  assets: AssetSummary[];
}

export function SettingsPage({ governance, assets }: SettingsPageProps) {
  return (
    <div className="panel-stack">
      <section className="panel-stack">
        <div className="section-heading">
          <h3>Governance overview</h3>
          <span>{governance.orgId}</span>
        </div>
        <div className="list-stack">
          <article className="list-card">
            <div className="list-card__row">
              <strong>Pending approvals</strong>
              <span className="risk-pill risk-pill--attention">{governance.pendingApprovals.length}</span>
            </div>
            <p className="list-card__body list-card__body--muted">
              {governance.secretsHealth.attentionRevisionCount} active revisions need secret attention.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__row">
              <strong>Usage summary</strong>
              <span>{governance.usageSummary.totalCount} events</span>
            </div>
            <p className="list-card__body list-card__body--muted">
              {Object.entries(governance.usageSummary.byKind)
                .map(([kind, count]) => `${kind}: ${count}`)
                .join(" • ") || "No usage recorded."}
            </p>
          </article>
        </div>
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Secrets health</h3>
          <span>
            {governance.secretsHealth.configuredSecretCount}/{governance.secretsHealth.requiredSecretCount} configured
          </span>
        </div>
        <div className="list-stack">
          {governance.secretsHealth.revisions.map((revision) => (
            <article className="list-card" key={revision.agentRevisionId}>
              <div className="list-card__row">
                <strong>{revision.agentName}</strong>
                <span className={`risk-pill risk-pill--${revision.status}`}>{revision.status}</span>
              </div>
              <div className="list-card__row list-card__row--muted">
                <span>
                  {revision.businessId} / {revision.environment}
                </span>
                <span>
                  {revision.configuredSecretCount}/{revision.requiredSecretCount} configured
                </span>
              </div>
              <p className="list-card__body list-card__body--muted">
                {revision.missingSecrets.length > 0
                  ? `Missing: ${revision.missingSecrets.join(", ")}`
                  : `Configured: ${revision.configuredSecrets.join(", ") || "none required"}`}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Recent audit</h3>
          <span>{governance.recentAudit.length} events</span>
        </div>
        <div className="list-stack">
          {governance.recentAudit.map((event) => (
            <article className="list-card" key={event.id}>
              <div className="list-card__row">
                <strong>{event.summary}</strong>
                <span>{event.eventType}</span>
              </div>
              <p className="list-card__body list-card__body--muted">{event.createdAt}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Recent usage</h3>
          <span>{governance.recentUsage.length} entries</span>
        </div>
        <div className="list-stack">
          {governance.recentUsage.map((event) => (
            <article className="list-card" key={event.id}>
              <div className="list-card__row">
                <strong>{event.kind}</strong>
                <span>{event.count}</span>
              </div>
              <p className="list-card__body list-card__body--muted">
                {[event.sourceKind, event.createdAt].filter(Boolean).join(" • ")}
              </p>
            </article>
          ))}
        </div>
      </section>

      <ConnectLaterPanel assets={assets} />
    </div>
  );
}
