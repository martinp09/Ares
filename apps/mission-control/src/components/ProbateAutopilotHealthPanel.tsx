import type { MissionControlDataSource, ProbateAutopilotHealthData } from "../lib/api";

function BoolLabel({ value }: { value: boolean }) {
  return <strong>{value ? "true" : "false"}</strong>;
}

function CountCard({ label, value }: { label: string; value: number | string }) {
  return (
    <article className="summary-card summary-card--compact">
      <p className="summary-card__label">{label}</p>
      <strong className="summary-card__value">{value}</strong>
    </article>
  );
}

function formatAge(hours: number | null): string {
  if (hours === null) {
    return "unknown";
  }
  if (hours < 1) {
    return `${Math.round(hours * 60)}m`;
  }
  return `${hours.toFixed(1)}h`;
}

function titleize(value: string): string {
  return value.replaceAll("_", " ");
}

export interface ProbateAutopilotHealthPanelProps {
  data: ProbateAutopilotHealthData;
  dataSource: MissionControlDataSource;
}

export function ProbateAutopilotHealthPanel({ data, dataSource }: ProbateAutopilotHealthPanelProps) {
  const hasActions = data.operatorNextActions.length > 0;
  const hasAnomalies = data.anomalies.length > 0;
  const duplicateCountByCounty = Object.entries(data.sourceQuality.duplicateCaseCountByCounty);

  return (
    <section className="panel-stack" aria-label="probate autopilot health">
      <div className="section-heading">
        <div>
          <h3>Probate autopilot health</h3>
          <p>
            Read-only source-run SLA for Harris + Montgomery probate. This panel never scrapes live sources, mirrors to CRM,
            enrolls, sends, calls, skiptraces, or dispatches providers.
          </p>
        </div>
        <span>{dataSource === "api" ? "API-backed" : "fixture fallback"}</span>
      </div>

      <div className="summary-grid summary-grid--secondary">
        <CountCard label="SLA status" value={data.status} />
        <CountCard label="Source runs" value={data.sourceRunCount} />
        <CountCard label="New records" value={data.newRecordCount} />
        <CountCard label="Warnings" value={data.warningCount} />
        <CountCard label="Brief age" value={formatAge(data.briefAgeHours)} />
        <CountCard label="Anomalies" value={data.anomalyCount} />
      </div>

      <div className="summary-grid summary-grid--secondary">
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Safety gates</p>
          <strong className="summary-card__value summary-card__value--status">no-send</strong>
          <ul>
            <li>No-send OK: <BoolLabel value={data.noSendOk} /></li>
            <li>Freshness OK: <BoolLabel value={data.freshnessOk} /></li>
            <li>Outbound allowed: <BoolLabel value={data.outboundAllowed} /></li>
            <li>Stale brief: <BoolLabel value={data.staleBrief} /></li>
          </ul>
        </article>

        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">County SLA</p>
          <strong className="summary-card__value summary-card__value--status">{data.slaHealth.status}</strong>
          <ul>
            <li>Expected: <strong>{data.slaHealth.expectedCounties.join(", ") || "none"}</strong></li>
            <li>Missing: <strong>{data.slaHealth.missingCounties.join(", ") || "none"}</strong></li>
            <li>Completed: <strong>{data.slaHealth.completedCountyCount}</strong></li>
            <li>Failed lanes: <strong>{data.slaHealth.failedLaneCount}</strong></li>
          </ul>
        </article>

        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Source quality</p>
          <strong className="summary-card__value summary-card__value--status">aggregate only</strong>
          <ul>
            <li>Mismatches: <strong>{data.sourceQuality.sourceCountMismatchCount}</strong></li>
            <li>Invalid rows: <strong>{data.sourceQuality.invalidRowCount}</strong></li>
            <li>Duplicate case rows: <strong>{data.sourceQuality.duplicateCaseCount}</strong></li>
            <li>Artifact warnings: <strong>{data.sourceQuality.artifactWarningCount}</strong></li>
          </ul>
          {duplicateCountByCounty.length > 0 ? (
            <p>Duplicate rows by county: {duplicateCountByCounty.map(([county, count]) => `${county}: ${count}`).join(", ")}</p>
          ) : null}
        </article>

        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Enrichment backlog</p>
          <strong className="summary-card__value summary-card__value--status">blocked until enriched</strong>
          <ul>
            <li>Property match: <strong>{data.enrichmentBacklog.propertyMatchPendingCount}</strong></li>
            <li>Tax overlay: <strong>{data.enrichmentBacklog.taxOverlayPendingCount}</strong></li>
            <li>HubSpot approval blocked: <strong>{data.enrichmentBacklog.hubSpotMirrorBlockedUntilApprovalCount}</strong></li>
            <li>Outbound approval blocked: <strong>{data.enrichmentBacklog.outboundBlockedUntilExplicitApprovalCount}</strong></li>
          </ul>
        </article>
      </div>

      <div className="summary-grid summary-grid--secondary">
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Operator next actions</p>
          <strong className="summary-card__value summary-card__value--status">{hasActions ? "queued" : "clear"}</strong>
          <div className="table-card" role="list" aria-label="probate autopilot next actions">
            {(hasActions ? data.operatorNextActions : [{ priority: "normal", action: "monitor_next_scheduled_pull", reason: "No next action is currently required." }]).map((action) => (
              <div className="table-card__row" role="listitem" key={`${action.priority}-${action.action}-${action.reason}`}>
                <span>{action.priority}</span>
                <strong>{titleize(action.action)}</strong>
                <span>{action.reason}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Anomaly watch</p>
          <strong className="summary-card__value summary-card__value--status">{hasAnomalies ? "attention" : "clear"}</strong>
          <div className="table-card" role="list" aria-label="probate autopilot anomalies">
            {(hasAnomalies ? data.anomalies : [{ severity: "normal", type: "none", message: "No source anomalies are currently surfaced." }]).map((anomaly) => (
              <div className="table-card__row" role="listitem" key={`${anomaly.severity}-${anomaly.type}-${anomaly.message}`}>
                <span>{anomaly.severity}</span>
                <strong>{titleize(anomaly.type)}</strong>
                <span>{anomaly.message}</span>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
