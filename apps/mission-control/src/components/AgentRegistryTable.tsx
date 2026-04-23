import type { AgentSummary } from "../lib/api";

interface AgentRegistryTableProps {
  agents: AgentSummary[];
  onSelectAgent?: (agentId: string) => void;
  selectedAgentId?: string | null;
}

export function AgentRegistryTable({ agents, onSelectAgent, selectedAgentId }: AgentRegistryTableProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Agent registry</h3>
        <span>{agents.length} tracked</span>
      </div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Revision</th>
              <th>Environment</th>
              <th>Live sessions</th>
              <th>Delegated work</th>
              <th>Lifecycle</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => {
              const isSelected = selectedAgentId === agent.id;
              return (
                <tr aria-current={isSelected ? "true" : undefined} key={agent.id}>
                  <td>
                    <strong>{agent.name}</strong>
                    <div className="data-table__meta">{agent.id}</div>
                  </td>
                  <td>{agent.activeRevisionState}</td>
                  <td>{agent.environment}</td>
                  <td>{agent.liveSessionCount}</td>
                  <td>{agent.delegatedWorkCount}</td>
                  <td>
                    <button
                      className={`workspace-switcher__item${isSelected ? " workspace-switcher__item--active" : ""}`}
                      onClick={() => onSelectAgent?.(agent.id)}
                      type="button"
                    >
                      {isSelected ? `Viewing ${agent.name}` : `View lifecycle for ${agent.name}`}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
