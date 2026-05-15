import type { ProviderOperationsData } from "../lib/api";

function CountPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="summary-card summary-card--compact">
      <p className="summary-card__label">{label}</p>
      <strong className="summary-card__value">{value}</strong>
    </div>
  );
}

function StatusLine({ label, value }: { label: string; value: string | boolean | number }) {
  return (
    <li>
      <span>{label}</span>: <strong>{typeof value === "boolean" ? String(value) : value}</strong>
    </li>
  );
}

export interface ProviderOperationsPanelProps {
  data: ProviderOperationsData;
}

export function ProviderOperationsPanel({ data }: ProviderOperationsPanelProps) {
  return (
    <section className="panel-stack" aria-label="provider operations preview">
      <div className="section-heading">
        <div>
          <h3>Provider operations</h3>
          <p>No-live read/preview status only. This panel never applies, sends, enrolls, dispatches, or places calls.</p>
        </div>
        <span>Provider writes gated</span>
      </div>

      <div className="summary-grid summary-grid--secondary">
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">HubSpot mirror preview</p>
          <strong className="summary-card__value summary-card__value--status">{data.hubspot.liveGateStatus}</strong>
          <ul>
            <StatusLine label="would-call-provider" value={data.hubspot.wouldCallProvider} />
            <StatusLine label="customization payloads" value={data.hubspot.customizationPayloadCount} />
            <StatusLine label="record payloads" value={data.hubspot.recordPayloadCount} />
            <StatusLine label="warnings" value={data.hubspot.warningCount} />
          </ul>
        </article>

        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Instantly enrollment preview</p>
          <strong className="summary-card__value summary-card__value--status">no-live preview</strong>
          <ul>
            <StatusLine label="would-call-provider" value={data.instantly.wouldCallProvider} />
          </ul>
          <div className="summary-grid summary-grid--secondary">
            <CountPill label="Eligible" value={data.instantly.counts.eligible} />
            <CountPill label="Submitted" value={data.instantly.counts.submitted} />
            <CountPill label="Enrolled" value={data.instantly.counts.enrolled} />
            <CountPill label="Skipped" value={data.instantly.counts.skipped} />
            <CountPill label="Excluded" value={data.instantly.counts.excluded} />
            <CountPill label="Errors" value={data.instantly.counts.errors} />
          </div>
        </article>

        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Vapi voice readiness</p>
          <strong className="summary-card__value summary-card__value--status">dry-run only</strong>
          <ul>
            <StatusLine label="assistants configured" value={data.vapi.assistantCount} />
            <StatusLine label="phone numbers configured" value={data.vapi.phoneNumberCount} />
            <StatusLine label="default assistant" value={data.vapi.defaultAssistantConfigured} />
            <StatusLine label="default phone number" value={data.vapi.defaultPhoneNumberConfigured} />
            <StatusLine label="live gate" value={data.vapi.liveGateStatus} />
            <StatusLine label="outbound dry-run" value={data.vapi.outboundDryRunStatus} />
          </ul>
          <p>No live voice call action is available in this slice.</p>
        </article>

        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Nightly brief / source runs</p>
          <strong className="summary-card__value summary-card__value--status">read-only ledger</strong>
          <ul>
            <StatusLine label="brief status" value={data.nightly.latestBriefStatus} />
            <StatusLine label="records reviewed" value={data.nightly.latestBriefRecordCount} />
            <StatusLine label="warnings" value={data.nightly.latestBriefWarningCount} />
            <StatusLine label="live source calls" value={data.nightly.liveSourceCallsEnabled} />
          </ul>
          <div className="table-card" role="list" aria-label="source run rows">
            {data.nightly.sourceRuns.map((run) => (
              <div className="table-card__row" role="listitem" key={`${run.sourceLane}-${run.status}`}>
                <span>{run.sourceLane}</span>
                <strong>{run.status}</strong>
                <span>{run.recordCount} records</span>
                <span>{run.warningCount} warnings</span>
              </div>
            ))}
          </div>
          <p>No live county, tax, land-record, or source provider call is available.</p>
        </article>
      </div>
    </section>
  );
}
