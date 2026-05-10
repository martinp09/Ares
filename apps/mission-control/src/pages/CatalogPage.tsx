import { AgentInstallWizard, type CatalogInstallUiState } from "../components/AgentInstallWizard";
import type { CatalogEntrySummary } from "../lib/api";

interface CatalogPageProps {
  entries: CatalogEntrySummary[];
  installEnabled: boolean;
  installDisabledReason?: string;
  hasActiveSearch: boolean;
  installStates: Record<string, CatalogInstallUiState | undefined>;
  onInstall: (entryId: string, request: { businessId: string; environment: string; name: string }) => void | Promise<void>;
  selectedBusinessId: string | null;
  selectedEnvironment: string | null;
}

function joinValues(values: string[]): string {
  return values.length > 0 ? values.join(", ") : "none";
}

function formatVisibility(value: string): string {
  return value.replace(/_/g, " ");
}

export function CatalogPage({
  entries,
  installEnabled,
  installDisabledReason,
  hasActiveSearch,
  installStates,
  onInstall,
  selectedBusinessId,
  selectedEnvironment,
}: CatalogPageProps) {
  const secretHeavyCount = entries.filter((entry) => entry.requiredSecretNames.length > 0).length;
  const skillHeavyCount = entries.filter((entry) => entry.requiredSkillIds.length > 0).length;
  const publishReadyCount = entries.filter((entry) => entry.marketplacePublicationEnabled).length;

  return (
    <div className="crm-page">
      <section className="crm-hero-panel crm-hero-panel--compact">
        <div className="crm-hero-panel__copy">
          <span>Agent catalog</span>
          <h3>Installable agent library</h3>
          <p>Install proven agent revisions into a selected target scope after verifying secrets, skills, and runtime compatibility.</p>
        </div>
        <div className="crm-hero-panel__stats" aria-label="Catalog readiness metrics">
          <article>
            <strong>{entries.length}</strong>
            <span>entries</span>
          </article>
          <article>
            <strong>{secretHeavyCount}</strong>
            <span>need secrets</span>
          </article>
          <article>
            <strong>{skillHeavyCount}</strong>
            <span>need skills</span>
          </article>
          <article>
            <strong>{publishReadyCount}</strong>
            <span>publish ready</span>
          </article>
        </div>
      </section>

      <div className="crm-control-bar" aria-label="Catalog controls">
        <span className="crm-control-pill">Scope: {selectedBusinessId ?? "choose business"} / {selectedEnvironment ?? "choose environment"}</span>
        <span className="crm-control-pill">{installEnabled ? "Install enabled" : "Read-only catalog"}</span>
        <button type="button" className="crm-control-button">Filter</button>
        <button type="button" className="crm-control-button">Sort: readiness</button>
        <button type="button" className="crm-control-button">Manage requirements</button>
      </div>

      {entries.length === 0 ? (
        <section className="crm-empty-state">
          <p className="panel-copy">
            {hasActiveSearch
              ? "No catalog entries match the current search."
              : "No catalog entries are available for the current org scope."}
          </p>
        </section>
      ) : (
        <div className="catalog-grid">
          {entries.map((entry) => (
            <section className="catalog-card" key={entry.id}>
              <div className="catalog-card__header">
                <div>
                  <span>{entry.slug}</span>
                  <h3>{entry.name}</h3>
                  <p>{entry.summary}</p>
                </div>
                <strong>{formatVisibility(entry.visibility)}</strong>
              </div>
              {entry.description ? <p className="panel-copy">{entry.description}</p> : null}
              <div className="catalog-card__meta">
                <article>
                  <p className="summary-card__label">Visibility</p>
                  <strong className="summary-card__value">{formatVisibility(entry.visibility)}</strong>
                </article>
                <article>
                  <p className="summary-card__label">Marketplace status</p>
                  <strong className="summary-card__value">
                    {entry.marketplacePublicationEnabled ? "Publication enabled" : "Public launch disabled"}
                  </strong>
                </article>
                <article>
                  <p className="summary-card__label">Host adapter</p>
                  <strong className="summary-card__value">{entry.hostAdapterKind}</strong>
                </article>
                <article>
                  <p className="summary-card__label">Provider</p>
                  <strong className="summary-card__value">{entry.providerKind}</strong>
                </article>
                <article>
                  <p className="summary-card__label">Release channel</p>
                  <strong className="summary-card__value">{entry.releaseChannel}</strong>
                </article>
              </div>
              <div className="catalog-requirements">
                <article>
                  <div className="list-card__row">
                    <strong>Required secrets</strong>
                    <span>{entry.requiredSecretNames.length}</span>
                  </div>
                  <p className="list-card__body list-card__body--muted">{joinValues(entry.requiredSecretNames)}</p>
                </article>
                <article>
                  <div className="list-card__row">
                    <strong>Required skills</strong>
                    <span>{entry.requiredSkillIds.length}</span>
                  </div>
                  <p className="list-card__body list-card__body--muted">{joinValues(entry.requiredSkillIds)}</p>
                </article>
                <article>
                  <div className="list-card__row">
                    <strong>Provider capabilities</strong>
                    <span>{entry.providerCapabilities.length}</span>
                  </div>
                  <p className="list-card__body list-card__body--muted">{joinValues(entry.providerCapabilities)}</p>
                </article>
              </div>
              <AgentInstallWizard
                entry={entry}
                installEnabled={installEnabled}
                installDisabledReason={installDisabledReason}
                installState={installStates[entry.id]}
                onInstall={onInstall}
                selectedBusinessId={selectedBusinessId}
                selectedEnvironment={selectedEnvironment}
              />
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
