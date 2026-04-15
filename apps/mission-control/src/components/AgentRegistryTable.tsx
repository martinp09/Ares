import type { AgentSummary } from "../lib/api";

interface AgentRegistryTableProps {
  agents: AgentSummary[];
}

export function AgentRegistryTable({ agents }: AgentRegistryTableProps) {
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
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr key={agent.id}>
                <td>
                  <strong>{agent.name}</strong>
                  <div className="data-table__meta">{agent.id}</div>
                </td>
                <td>{agent.activeRevisionState}</td>
                <td>{agent.environment}</td>
                <td>{agent.liveSessionCount}</td>
                <td>{agent.delegatedWorkCount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
