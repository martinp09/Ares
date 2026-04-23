import type { AgentHostAdapterSummary } from "../lib/api";

interface HostAdapterBadgeProps {
  hostAdapter?: AgentHostAdapterSummary;
  revisionHostAdapterKind?: string;
  compatibilityWarnings?: string[];
}

function summarizeCapabilities(hostAdapter?: AgentHostAdapterSummary): string | null {
  if (!hostAdapter) {
    return null;
  }

  const capabilities = [
    hostAdapter.capabilities.dispatch ? "dispatch" : null,
    hostAdapter.capabilities.statusCorrelation ? "status correlation" : null,
    hostAdapter.capabilities.artifactReporting ? "artifact reporting" : null,
    hostAdapter.capabilities.cancellation ? "cancellation" : null,
  ].filter(Boolean);

  return `${hostAdapter.adapterDetailsLabel}: ${capabilities.length > 0 ? capabilities.join(", ") : "none"}`;
}

function formatAdapterFallback(kind: string): string {
  return kind
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(".");
}

export function HostAdapterBadge({ hostAdapter, revisionHostAdapterKind, compatibilityWarnings = [] }: HostAdapterBadgeProps) {
  const adapterLabel = hostAdapter?.displayName ?? (revisionHostAdapterKind ? formatAdapterFallback(revisionHostAdapterKind) : "Host adapter");
  const statusLabel = hostAdapter ? `${adapterLabel} ${hostAdapter.enabled ? "enabled" : "disabled"}` : `${adapterLabel} status unavailable`;
  const adapterDetailsSummary = summarizeCapabilities(hostAdapter);

  return (
    <div className="list-card__row list-card__row--muted">
      <span>{statusLabel}</span>
      <span>{hostAdapter?.kind ?? revisionHostAdapterKind ?? "unknown"}</span>
      {adapterDetailsSummary ? <span>{adapterDetailsSummary}</span> : null}
      {hostAdapter?.disabledReason ? <span>{hostAdapter.disabledReason}</span> : null}
      {compatibilityWarnings.map((warning) => (
        <span key={warning}>{warning}</span>
      ))}
    </div>
  );
}
