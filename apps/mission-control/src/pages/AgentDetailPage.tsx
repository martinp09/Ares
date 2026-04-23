import type { AgentDetailData, AgentDetailDegradedSection, AgentReleaseEvent } from "../lib/api";

interface AgentDetailPageProps {
  detail: AgentDetailData;
  dataSource: "api" | "fixture" | "degraded";
  onBack: () => void;
}

function formatList(values: string[]): string {
  return values.length > 0 ? values.join(", ") : "None declared";
}

function sectionIsDegraded(detail: AgentDetailData, section: AgentDetailDegradedSection): boolean {
  return (detail.degradedSections ?? []).includes(section);
}

export function AgentDetailPage({ detail, dataSource, onBack }: AgentDetailPageProps) {
  const activeRevision = detail.revisions.find((revision) => revision.id === detail.agent.activeRevisionId) ?? detail.revisions[0];
  const latestRelease = detail.releaseHistory.reduce<AgentReleaseEvent | undefined>(
    (latest, event) => (!latest || event.createdAt > latest.createdAt ? event : latest),
    undefined,
  );
  const usageKinds = Object.entries(detail.usageSummary.byKind);

  return (
    <div className="page-stack">
      <section className="panel-stack">
        <div className="section-heading">
          <div>
            <h3>Agent lifecycle</h3>
            <p>
              {detail.agent.name} · {detail.agent.businessId} · {detail.agent.environment}
            </p>
          </div>
          <span>
            {dataSource === "fixture"
              ? "Fixture fallback"
              : dataSource === "degraded"
                ? "Live detail unavailable"
                : detail.degradedSections.length > 0
                  ? "Live detail (partial)"
                  : "Live detail"}
          </span>
        </div>
        <p className="panel-copy">
          Read-only lifecycle view for the selected agent. Publish and rollback stay runtime-owned until a later slice wires
          real controls.
        </p>
        <div className="workspace-switcher">
          <button className="workspace-switcher__item" onClick={onBack} type="button">
            Back to agents
          </button>
          <span className="status-badge">{detail.agent.activeRevisionState}</span>
          <span className="status-badge">{detail.agent.lifecycleStatus}</span>
        </div>
        <div className="summary-grid summary-grid--secondary">
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Active revision</p>
            <strong className="summary-card__value">{detail.agent.activeRevisionId ?? "None"}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Revision count</p>
            <strong className="summary-card__value">
              {sectionIsDegraded(detail, "revisions") ? "Unavailable" : detail.revisions.length}
            </strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Release history</p>
            <strong className="summary-card__value">
              {sectionIsDegraded(detail, "releaseHistory") ? "Unavailable" : detail.releaseHistory.length}
            </strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Recent turns</p>
            <strong className="summary-card__value">
              {sectionIsDegraded(detail, "recentTurns") ? "Unavailable" : detail.recentTurns.length}
            </strong>
          </article>
        </div>
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Current posture</h3>
          <span>{sectionIsDegraded(detail, "revisions") ? "Revision data unavailable" : activeRevision ? `Revision ${activeRevision.revisionNumber}` : "No revision selected"}</span>
        </div>
        {activeRevision ? (
          <div className="list-stack">
            <article className="list-card">
              <div className="list-card__row">
                <strong>{activeRevision.id}</strong>
                <span>{activeRevision.state}</span>
              </div>
              <p className="list-card__body">
                Adapter {activeRevision.hostAdapterKind} · Provider {activeRevision.providerKind}
              </p>
              <div className="list-card__row list-card__row--muted">
                <span>Capabilities: {formatList(activeRevision.providerCapabilities)}</span>
                <span>Release channel: {activeRevision.releaseChannel}</span>
              </div>
              <div className="list-card__row list-card__row--muted">
                <span>Skills: {formatList(activeRevision.skillIds)}</span>
                <span>Required secrets: {activeRevision.requiredSecrets.length}</span>
              </div>
              {activeRevision.releaseNotes ? <p className="list-card__body list-card__body--muted">{activeRevision.releaseNotes}</p> : null}
            </article>
            <article className="list-card">
              <div className="list-card__row">
                <strong>Release control status</strong>
                <span>{sectionIsDegraded(detail, "releaseHistory") ? "unavailable" : latestRelease ? latestRelease.eventType : "unreleased"}</span>
              </div>
              <p className="list-card__body">
                {sectionIsDegraded(detail, "releaseHistory")
                  ? "Release history is temporarily unavailable from the current live read models."
                  : latestRelease
                    ? `Latest event ${latestRelease.id} moved ${latestRelease.targetRevisionId} to ${latestRelease.resultingActiveRevisionId}.`
                    : "No release events are recorded for this agent yet."}
              </p>
              <p className="list-card__body list-card__body--muted">
                No publish or rollback buttons are exposed in this bounded slice.
              </p>
            </article>
          </div>
        ) : sectionIsDegraded(detail, "revisions") ? (
          <p className="panel-copy">Revision data is temporarily unavailable from the current live read models.</p>
        ) : (
          <p className="panel-copy">No revision data is available for this agent.</p>
        )}
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Revision history</h3>
          <span>{sectionIsDegraded(detail, "revisions") ? "unavailable" : `${detail.revisions.length} tracked`}</span>
        </div>
        {sectionIsDegraded(detail, "revisions") ? (
          <p className="panel-copy">Revision history is temporarily unavailable from the current live read models.</p>
        ) : detail.revisions.length > 0 ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Revision</th>
                  <th>State</th>
                  <th>Adapter / provider</th>
                  <th>Skills</th>
                  <th>Secrets</th>
                </tr>
              </thead>
              <tbody>
                {detail.revisions.map((revision) => (
                  <tr key={revision.id}>
                    <td>
                      <strong>{`r${revision.revisionNumber}`}</strong>
                      <div className="data-table__meta">{revision.id}</div>
                    </td>
                    <td>{revision.state}</td>
                    <td>
                      {revision.hostAdapterKind} / {revision.providerKind}
                      <div className="data-table__meta">{revision.releaseChannel}</div>
                    </td>
                    <td>{formatList(revision.skillIds)}</td>
                    <td>{revision.requiredSecrets.length > 0 ? formatList(revision.requiredSecrets) : "None declared"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="panel-copy">No revisions are recorded for this agent yet.</p>
        )}
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Secrets health</h3>
          <span>
            {sectionIsDegraded(detail, "secretsHealth")
              ? "unavailable"
              : detail.secretsHealth?.status ?? "not configured"}
          </span>
        </div>
        {detail.secretsHealth ? (
          <div className="summary-grid summary-grid--secondary">
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Required</p>
              <strong className="summary-card__value">{detail.secretsHealth.requiredSecretCount}</strong>
            </article>
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Configured</p>
              <strong className="summary-card__value">{detail.secretsHealth.configuredSecretCount}</strong>
            </article>
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Missing</p>
              <strong className="summary-card__value">{detail.secretsHealth.missingSecretCount}</strong>
            </article>
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Active revision</p>
              <strong className="summary-card__value">{detail.secretsHealth.revisionId}</strong>
            </article>
          </div>
        ) : sectionIsDegraded(detail, "secretsHealth") ? (
          <p className="panel-copy">Secrets health is temporarily unavailable from the current live read models.</p>
        ) : (
          <p className="panel-copy">No active revision secrets posture is available.</p>
        )}
        {detail.secretsHealth ? (
          <ul className="detail-list">
            <li>Required: {formatList(detail.secretsHealth.requiredSecrets)}</li>
            <li>Configured: {formatList(detail.secretsHealth.configuredSecrets)}</li>
            <li>Missing: {formatList(detail.secretsHealth.missingSecrets)}</li>
          </ul>
        ) : null}
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Release history</h3>
          <span>{sectionIsDegraded(detail, "releaseHistory") ? "unavailable" : `${detail.releaseHistory.length} events`}</span>
        </div>
        {detail.releaseHistory.length > 0 ? (
          <div className="list-stack">
            {detail.releaseHistory.map((event) => (
              <article className="list-card" key={event.id}>
                <div className="list-card__row">
                  <strong>{event.eventType}</strong>
                  <span>{event.createdAt}</span>
                </div>
                <p className="list-card__body">
                  Target {event.targetRevisionId} · active {event.resultingActiveRevisionId}
                </p>
                <div className="list-card__row list-card__row--muted">
                  <span>{event.releaseChannel ?? "internal"}</span>
                  <span>{`${event.actorType}:${event.actorId}`}</span>
                </div>
                {event.evaluation ? (
                  <p className="list-card__body list-card__body--muted">
                    {event.evaluation.evaluatorResult}
                    {event.evaluation.rollbackReason ? ` · ${event.evaluation.rollbackReason}` : ""}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        ) : sectionIsDegraded(detail, "releaseHistory") ? (
          <p className="panel-copy">Release history is temporarily unavailable from the current live read models.</p>
        ) : (
          <p className="panel-copy">Release history has not started for this agent yet.</p>
        )}
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Usage</h3>
          <span>{sectionIsDegraded(detail, "usage") ? "unavailable" : `${detail.usageSummary.totalCount} tracked events`}</span>
        </div>
        <div className="summary-grid summary-grid--secondary">
          {sectionIsDegraded(detail, "usage") ? (
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Usage data</p>
              <strong className="summary-card__value">Unavailable</strong>
            </article>
          ) : usageKinds.length > 0 ? (
            usageKinds.map(([kind, count]) => (
              <article className="summary-card summary-card--compact" key={kind}>
                <p className="summary-card__label">{kind}</p>
                <strong className="summary-card__value">{count}</strong>
              </article>
            ))
          ) : (
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Usage</p>
              <strong className="summary-card__value">0</strong>
            </article>
          )}
        </div>
        {detail.recentUsage.length > 0 ? (
          <ul className="detail-list">
            {detail.recentUsage.map((event) => (
              <li key={event.id}>
                {event.kind} · {event.count}
                {event.sourceKind ? ` · ${event.sourceKind}` : ""} · {event.createdAt}
              </li>
            ))}
          </ul>
        ) : sectionIsDegraded(detail, "usage") ? (
          <p className="panel-copy">Usage data is temporarily unavailable from the current live read models.</p>
        ) : (
          <p className="panel-copy">No usage events are visible for this agent.</p>
        )}
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Recent audit</h3>
          <span>{sectionIsDegraded(detail, "recentAudit") ? "unavailable" : `${detail.recentAudit.length} events`}</span>
        </div>
        {detail.recentAudit.length > 0 ? (
          <div className="list-stack">
            {detail.recentAudit.map((event) => (
              <article className="list-card" key={event.id}>
                <div className="list-card__row">
                  <strong>{event.eventType}</strong>
                  <span>{event.createdAt}</span>
                </div>
                <p className="list-card__body">{event.summary}</p>
                <div className="list-card__row list-card__row--muted">
                  <span>{event.resourceType ?? "resource"}</span>
                  <span>{event.resourceId ?? "n/a"}</span>
                </div>
              </article>
            ))}
          </div>
        ) : sectionIsDegraded(detail, "recentAudit") ? (
          <p className="panel-copy">Audit data is temporarily unavailable from the current live read models.</p>
        ) : (
          <p className="panel-copy">No audit events are currently available for this agent.</p>
        )}
      </section>

      <section className="panel-stack" aria-label="Recent turns">
        <div className="section-heading">
          <h3>Recent turns</h3>
          <span>{sectionIsDegraded(detail, "recentTurns") ? "unavailable" : `${detail.recentTurns.length} visible`}</span>
        </div>
        {detail.recentTurns.length > 0 ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Turn</th>
                  <th>Revision</th>
                  <th>State</th>
                  <th>Retry count</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {detail.recentTurns.map((turn) => (
                  <tr key={turn.id}>
                    <td>
                      <strong>{turn.turnNumber}</strong>
                      <div className="data-table__meta">{turn.sessionId}</div>
                    </td>
                    <td>{turn.agentRevisionId}</td>
                    <td>{turn.state}</td>
                    <td>{turn.retryCount}</td>
                    <td>{turn.updatedAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : sectionIsDegraded(detail, "recentTurns") ? (
          <p className="panel-copy">Recent turns are temporarily unavailable from the current live read models.</p>
        ) : (
          <p className="panel-copy">No recent turns are available from the current read models.</p>
        )}
      </section>
    </div>
  );
}
