import { AgentRegistryTable } from "../components/AgentRegistryTable";
import type { AgentSummary } from "../lib/api";

interface AgentsPageProps {
  agents: AgentSummary[];
}

function getPublishedCount(agents: AgentSummary[]): number {
  return agents.filter((agent) => agent.activeRevisionState === "published").length;
}

export function AgentsPage({ agents }: AgentsPageProps) {
  const publishedCount = getPublishedCount(agents);
  const environmentCount = new Set(agents.map((agent) => agent.environment)).size;
  const liveSessionCount = agents.reduce((total, agent) => total + agent.liveSessionCount, 0);
  const delegatedWorkCount = agents.reduce((total, agent) => total + agent.delegatedWorkCount, 0);
  const featuredAgent = agents[0];

  return (
    <div className="page-stack">
      <section className="panel-stack">
        <div className="section-heading">
          <h3>Agent platform cockpit</h3>
          <span>Fixture-backed / no Supabase wiring</span>
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
        </div>
        <p className="panel-copy">
          Agents are the product unit here. The rest is just scaffolding until live runtime wiring is turned on later.
        </p>
        {featuredAgent ? (
          <p className="panel-copy">
            Featured agent: {featuredAgent.name} — {featuredAgent.activeRevisionState} in {featuredAgent.environment}.
          </p>
        ) : null}
      </section>

      <AgentRegistryTable agents={agents} />
    </div>
  );
}
