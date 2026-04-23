import { useEffect, useState } from "react";

import type { CatalogEntrySummary } from "../lib/api";

export interface CatalogInstallUiState {
  status: "submitting" | "succeeded" | "failed";
  message: string;
}

interface AgentInstallWizardProps {
  entry: CatalogEntrySummary;
  selectedBusinessId: string | null;
  selectedEnvironment: string | null;
  installEnabled: boolean;
  installDisabledReason?: string;
  installState?: CatalogInstallUiState;
  onInstall: (entryId: string, request: { businessId: string; environment: string; name: string }) => void | Promise<void>;
}

export function AgentInstallWizard({
  entry,
  selectedBusinessId,
  selectedEnvironment,
  installEnabled,
  installDisabledReason,
  installState,
  onInstall,
}: AgentInstallWizardProps) {
  const [businessId, setBusinessId] = useState(selectedBusinessId ?? "default");
  const [environment, setEnvironment] = useState(selectedEnvironment ?? "dev");
  const [name, setName] = useState(entry.name);

  useEffect(() => {
    setBusinessId(selectedBusinessId ?? "default");
  }, [selectedBusinessId]);

  useEffect(() => {
    setEnvironment(selectedEnvironment ?? "dev");
  }, [selectedEnvironment]);

  useEffect(() => {
    setName(entry.name);
  }, [entry.id, entry.name]);

  const isSubmitting = installState?.status === "submitting";
  const isDisabled = !installEnabled || isSubmitting || !businessId.trim() || !environment.trim() || !name.trim();

  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h4>Install into runtime</h4>
        <span>{entry.releaseChannel}</span>
      </div>
      <p className="panel-copy">Prefilled from the current filters; changing them installs outside the current filtered view.</p>
      <label className="search-field">
        <span className="search-field__label">Installed agent name</span>
        <input value={name} onChange={(event) => setName(event.target.value)} />
      </label>
      <label className="search-field">
        <span className="search-field__label">Target business id</span>
        <input value={businessId} onChange={(event) => setBusinessId(event.target.value)} />
      </label>
      <label className="search-field">
        <span className="search-field__label">Target environment</span>
        <input value={environment} onChange={(event) => setEnvironment(event.target.value)} />
      </label>
      {installState ? (
        <p className="panel-copy" role="status">
          {installState.message}
        </p>
      ) : null}
      {!installEnabled && installDisabledReason ? <p className="panel-copy">{installDisabledReason}</p> : null}
      <button
        className="nav-item nav-item--active"
        disabled={isDisabled}
        onClick={() =>
          void onInstall(entry.id, {
            businessId: businessId.trim(),
            environment: environment.trim(),
            name: name.trim(),
          })
        }
        type="button"
      >
        {isSubmitting ? `Installing ${entry.name}...` : `Install ${entry.name}`}
      </button>
    </section>
  );
}
