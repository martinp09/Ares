import { ConnectLaterPanel } from "../components/ConnectLaterPanel";
import type { AssetSummary, GovernanceData } from "../lib/api";
import { AuditPage } from "./AuditPage";
import { SecretsPage } from "./SecretsPage";
import { UsagePage } from "./UsagePage";

interface SettingsPageProps {
  governance: GovernanceData;
  assets: AssetSummary[];
}

function pendingApprovalsTone(pendingApprovalCount: number) {
  return pendingApprovalCount > 0 ? "attention" : "healthy";
}

function GovernanceOverviewSection({ governance }: Pick<SettingsPageProps, "governance">) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Governance overview</h3>
        <span>{governance.orgId}</span>
      </div>
      <p className="panel-copy">Governance stays org-scoped. Runtime asset bindings honor the selected business and environment filters.</p>
      <div className="list-stack">
        <article className="list-card">
          <div className="list-card__row">
            <strong>Pending approvals</strong>
            <span className={`risk-pill risk-pill--${pendingApprovalsTone(governance.pendingApprovals.length)}`}>
              {governance.pendingApprovals.length}
            </span>
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
  );
}

export function SettingsPage({ governance, assets }: SettingsPageProps) {
  return (
    <div className="crm-page">
      <section className="crm-hero-panel crm-hero-panel--compact">
        <div className="crm-hero-panel__copy">
          <span>Admin and governance</span>
          <h3>Control-room health</h3>
          <p>Admin controls keep org-wide approvals separate from business and environment runtime bindings.</p>
        </div>
        <div className="crm-hero-panel__stats" aria-label="Admin health metrics">
          <article>
            <strong>{governance.pendingApprovals.length}</strong>
            <span>approvals</span>
          </article>
          <article>
            <strong>{governance.secretsHealth.attentionRevisionCount}</strong>
            <span>secret alerts</span>
          </article>
          <article>
            <strong>{governance.recentAudit.length}</strong>
            <span>audit events</span>
          </article>
          <article>
            <strong>{assets.length}</strong>
            <span>assets</span>
          </article>
        </div>
      </section>
      <div className="crm-object-tabs" role="tablist" aria-label="Admin sections">
        <button type="button" role="tab" aria-selected="true" className="crm-object-tab crm-object-tab--active">Governance</button>
        <button type="button" role="tab" aria-selected="false" className="crm-object-tab">Secrets</button>
        <button type="button" role="tab" aria-selected="false" className="crm-object-tab">Audit</button>
        <button type="button" role="tab" aria-selected="false" className="crm-object-tab">Usage</button>
        <button type="button" role="tab" aria-selected="false" className="crm-object-tab">Assets</button>
      </div>
      <div className="admin-grid">
        <div className="admin-grid__primary">
          <GovernanceOverviewSection governance={governance} />
          <SecretsPage secretsHealth={governance.secretsHealth} />
        </div>
        <div className="admin-grid__secondary">
          <AuditPage events={governance.recentAudit} />
          <UsagePage usageSummary={governance.usageSummary} recentUsage={governance.recentUsage} />
          <ConnectLaterPanel assets={assets} />
        </div>
      </div>
    </div>
  );
}
