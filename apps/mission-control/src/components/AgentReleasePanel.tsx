import type { AgentHostAdapterSummary, AgentReleaseEvent, AgentReleaseState, AgentRevisionDetail } from "../lib/api";
import { HostAdapterBadge } from "./HostAdapterBadge";

interface AgentReleasePanelProps {
  agentName: string;
  activeRevisionState: string;
  hostAdapter?: AgentHostAdapterSummary;
  release?: AgentReleaseState | AgentReleaseEvent;
  activeRevision?: AgentRevisionDetail;
  compatibilityWarnings?: string[];
}

function getReleaseStatus(activeRevisionState: string, release?: AgentReleaseState | AgentReleaseEvent): string {
  if (!release) {
    return activeRevisionState;
  }
  return release.eventType === "rollback" ? "rollback live" : `${release.eventType} live`;
}

export function AgentReleasePanel({
  agentName,
  activeRevisionState,
  hostAdapter,
  release,
  activeRevision,
  compatibilityWarnings = [],
}: AgentReleasePanelProps) {
  const releaseStatus = getReleaseStatus(activeRevisionState, release);
  const releaseChannel = release?.releaseChannel ?? activeRevision?.releaseChannel ?? "internal";
  const releaseTimestamp = release?.createdAt ?? activeRevision?.updatedAt ?? "Unknown";
  const revisionBody = release
    ? `Channel ${releaseChannel} · target ${release.targetRevisionId} · active ${release.resultingActiveRevisionId}`
    : activeRevision
      ? `Channel ${releaseChannel} · revision ${activeRevision.id} · state ${activeRevision.state}`
      : `Channel ${releaseChannel} · release posture unavailable until runtime history reconciles`;
  const lifecycleWarning = release?.evaluation && !release.evaluation.satisfied ? "Latest release evaluation failed." : null;

  return (
    <article className="list-card">
      <div className="list-card__row">
        <strong>{agentName}</strong>
        <span>{releaseStatus}</span>
      </div>
      <p className="list-card__body">{revisionBody}</p>
      <p className="list-card__body list-card__body--muted">Runtime owns publish and rollback. Mission Control is read-only in this slice.</p>
      <HostAdapterBadge
        compatibilityWarnings={[...(lifecycleWarning ? [lifecycleWarning] : []), ...compatibilityWarnings]}
        hostAdapter={hostAdapter}
        revisionHostAdapterKind={activeRevision?.hostAdapterKind}
      />
      <div className="list-card__row list-card__row--muted">
        <span>{activeRevision?.providerKind ? `Provider ${activeRevision.providerKind}` : `Release channel ${releaseChannel}`}</span>
        <span>{releaseTimestamp}</span>
      </div>
    </article>
  );
}
