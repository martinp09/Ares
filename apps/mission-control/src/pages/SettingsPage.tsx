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
    <div className="panel-stack">
      <GovernanceOverviewSection governance={governance} />
      <SecretsPage secretsHealth={governance.secretsHealth} />
      <AuditPage events={governance.recentAudit} />
      <UsagePage usageSummary={governance.usageSummary} recentUsage={governance.recentUsage} />
      <ConnectLaterPanel assets={assets} />
    </div>
  );
}
