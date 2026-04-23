import type { GovernanceData } from "../lib/api";

interface SecretHealthPanelProps {
  secretsHealth: GovernanceData["secretsHealth"];
}

function overviewTone(secretsHealth: GovernanceData["secretsHealth"]) {
  if (secretsHealth.revisions.length === 0) {
    return null;
  }

  return secretsHealth.attentionRevisionCount > 0 ? "attention" : "healthy";
}

function formatSecretPosture(configuredSecrets: string[], missingSecrets: string[]) {
  if (missingSecrets.length > 0) {
    return `Missing: ${missingSecrets.join(", ")}`;
  }

  return `Configured: ${configuredSecrets.join(", ") || "none required"}`;
}

function renderOverviewCopy(secretsHealth: GovernanceData["secretsHealth"]) {
  if (secretsHealth.revisions.length === 0) {
    return "No active revisions have reported secret requirements yet.";
  }

  if (secretsHealth.attentionRevisionCount > 0) {
    return `${secretsHealth.attentionRevisionCount} active revisions need secret attention.`;
  }

  return "All active revisions have their required secrets configured.";
}

export function SecretHealthPanel({ secretsHealth }: SecretHealthPanelProps) {
  const activeRevisionsTone = overviewTone(secretsHealth);

  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Secrets health</h3>
        <span>
          {secretsHealth.configuredSecretCount}/{secretsHealth.requiredSecretCount} configured
        </span>
      </div>
      <div className="list-stack">
        <article className="list-card">
          <div className="list-card__row">
            <strong>Active revisions</strong>
            <span className={activeRevisionsTone ? `risk-pill risk-pill--${activeRevisionsTone}` : "risk-pill"}>
              {secretsHealth.revisions.length === 0
                ? "empty"
                : `${secretsHealth.healthyRevisionCount}/${secretsHealth.activeRevisionCount} healthy`}
            </span>
          </div>
          <p className="list-card__body list-card__body--muted">{renderOverviewCopy(secretsHealth)}</p>
        </article>
        {secretsHealth.revisions.map((revision) => (
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
              {formatSecretPosture(revision.configuredSecrets, revision.missingSecrets)}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
