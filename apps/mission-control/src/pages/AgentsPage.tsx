import { AgentReleasePanel } from "../components/AgentReleasePanel";
import { AgentRegistryTable } from "../components/AgentRegistryTable";
import type { AgentSummary, MissionControlView } from "../lib/api";

export interface AgentsPageOperatorView {
  id: Extract<MissionControlView, "dashboard" | "inbox" | "approvals" | "runs">;
  label: string;
  metricLabel: string;
  metricValue: number;
  description: string;
}

interface AgentsPageProps {
  agents: AgentSummary[];
  dataSource?: "api" | "fixture";
  onSelectAgent?: (agentId: string) => void;
  selectedAgentId?: string | null;
  workspaceLabel: string;
  operatorViews: AgentsPageOperatorView[];
}

function getPublishedCount(agents: AgentSummary[]): number {
  return agents.filter((agent) => agent.activeRevisionState === "published").length;
}

function summarizeRelease(agent: AgentSummary): string {
  const release = agent.release;
  if (!release) {
    return `${agent.activeRevisionState} / release posture unavailable until runtime history reconciles`;
  }
  const evaluation = release.evaluation;
  const evaluationLabel = evaluation
    ? evaluation.satisfied
      ? `eval ${evaluation.status}`
      : `eval ${evaluation.status} (${evaluation.failureDetails.length} issues)`
    : "eval pending";
  return `${release.eventType} · ${release.releaseChannel ?? "internal"} · ${evaluationLabel}`;
}

export function AgentsPage({
  agents,
  dataSource = "fixture",
  workspaceLabel,
  operatorViews,
  onSelectAgent,
  selectedAgentId,
}: AgentsPageProps) {
  const publishedCount = getPublishedCount(agents);
  const environmentCount = new Set(agents.map((agent) => agent.environment)).size;
  const liveSessionCount = agents.reduce((total, agent) => total + agent.liveSessionCount, 0);
  const delegatedWorkCount = agents.reduce((total, agent) => total + agent.delegatedWorkCount, 0);
  const rollbackCount = agents.filter((agent) => agent.release?.eventType === "rollback").length;
  const failingEvalCount = agents.filter((agent) => agent.release?.evaluation && !agent.release.evaluation.satisfied).length;
  const featuredAgent = agents[0];
  return (
    <div className="page-stack">
      <section className="panel-stack">
        <div className="section-heading">
          <h3>Agent platform cockpit</h3>
          <span>{dataSource === "api" ? "Live API / no Supabase wiring" : "Fixture fallback / no Supabase wiring"}</span>
        </div>
        <div className="summary-grid summary-grid--secondary">
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Published revisions</p>
            <strong className="summary-card__value">{publishedCount}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Environments</p>
            <strong className="summary-card__value">{environmentCount}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Live sessions</p>
            <strong className="summary-card__value">{liveSessionCount}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Delegated work</p>
            <strong className="summary-card__value">{delegatedWorkCount}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Rollback-active agents</p>
            <strong className="summary-card__value">{rollbackCount}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Failing release evals</p>
            <strong className="summary-card__value">{failingEvalCount}</strong>
          </article>
        </div>
        <p className="panel-copy">
          Agents are the product unit here. The rest is just scaffolding until live runtime wiring is turned on later.
        </p>
        <p className="panel-copy">Select an agent from the registry to inspect revisions, release posture, secrets, audit, usage, and recent turns.</p>
        {featuredAgent ? (
          <p className="panel-copy">
            Featured agent: {featuredAgent.name} — {summarizeRelease(featuredAgent)} in {featuredAgent.environment}.
          </p>
        ) : null}
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Operator views around agents</h3>
          <span>{workspaceLabel} operator workspace</span>
        </div>
        <div className="summary-grid summary-grid--secondary">
          {operatorViews.map((view) => (
            <article className="summary-card summary-card--compact" key={view.id}>
              <p className="summary-card__label">{view.label}</p>
              <strong className="summary-card__value">{`${view.metricValue} ${view.metricLabel}`}</strong>
              <p className="panel-copy">{view.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Release posture</h3>
          <span>{agents.length} agents in scope</span>
        </div>
        {agents.length > 0 ? (
          <div className="list-stack">
            {agents.map((agent) => (
              <AgentReleasePanel
                key={`${agent.id}-release`}
                activeRevisionState={agent.activeRevisionState}
                agentName={agent.name}
                hostAdapter={agent.hostAdapter}
                release={agent.release}
              />
            ))}
          </div>
        ) : (
          <p className="panel-copy">No agents are available for the current scope yet.</p>
        )}
      </section>

      <AgentRegistryTable agents={agents} onSelectAgent={onSelectAgent} selectedAgentId={selectedAgentId} />
    </div>
  );
}
