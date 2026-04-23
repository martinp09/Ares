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
  return (
    <div className="page-stack">
      <section className="panel-stack">
        <div className="section-heading">
          <h3>Internal catalog</h3>
          <span>{entries.length} entries</span>
        </div>
        <p className="panel-copy">
          Install proven agent revisions into a selected target scope without changing their execution semantics.
        </p>
      </section>

      {entries.length === 0 ? (
        <section className="panel-stack">
          <p className="panel-copy">
            {hasActiveSearch
              ? "No catalog entries match the current search."
              : "No catalog entries are available for the current org scope."}
          </p>
        </section>
      ) : (
        <div className="list-stack">
          {entries.map((entry) => (
            <section className="panel-stack" key={entry.id}>
              <div className="section-heading">
                <h3>{entry.name}</h3>
                <span>{entry.slug}</span>
              </div>
              <p className="panel-copy">{entry.summary}</p>
              {entry.description ? <p className="panel-copy">{entry.description}</p> : null}
              <div className="summary-grid summary-grid--secondary">
                <article className="summary-card summary-card--compact">
                  <p className="summary-card__label">Visibility</p>
                  <strong className="summary-card__value">{formatVisibility(entry.visibility)}</strong>
                </article>
                <article className="summary-card summary-card--compact">
                  <p className="summary-card__label">Marketplace status</p>
                  <strong className="summary-card__value">
                    {entry.marketplacePublicationEnabled ? "Publication enabled" : "Public launch disabled"}
                  </strong>
                </article>
                <article className="summary-card summary-card--compact">
                  <p className="summary-card__label">Host adapter</p>
                  <strong className="summary-card__value">{entry.hostAdapterKind}</strong>
                </article>
                <article className="summary-card summary-card--compact">
                  <p className="summary-card__label">Provider</p>
                  <strong className="summary-card__value">{entry.providerKind}</strong>
                </article>
                <article className="summary-card summary-card--compact">
                  <p className="summary-card__label">Release channel</p>
                  <strong className="summary-card__value">{entry.releaseChannel}</strong>
                </article>
              </div>
              <div className="list-stack">
                <article className="list-card">
                  <div className="list-card__row">
                    <strong>Required secrets</strong>
                    <span>{entry.requiredSecretNames.length}</span>
                  </div>
                  <p className="list-card__body list-card__body--muted">{joinValues(entry.requiredSecretNames)}</p>
                </article>
                <article className="list-card">
                  <div className="list-card__row">
                    <strong>Required skills</strong>
                    <span>{entry.requiredSkillIds.length}</span>
                  </div>
                  <p className="list-card__body list-card__body--muted">{joinValues(entry.requiredSkillIds)}</p>
                </article>
                <article className="list-card">
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
