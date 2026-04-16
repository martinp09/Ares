import type { TurnSummary } from "../lib/api";

interface TurnTimelineProps {
  turns: TurnSummary[];
}

export function TurnTimeline({ turns }: TurnTimelineProps) {
  return (
    <section className="panel-stack" aria-label="Turn timeline">
      <div className="section-heading">
        <h3>Turn state and retries</h3>
        <span>{turns.length} visible</span>
      </div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Turn</th>
              <th>Scope</th>
              <th>State</th>
              <th>Retries</th>
              <th>Agent</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {turns.map((turn) => (
              <tr key={turn.id}>
                <td>
                  <strong>#{turn.turnNumber}</strong>
                  <div className="data-table__meta">{turn.id}</div>
                </td>
                <td>
                  <strong>{turn.sessionId}</strong>
                  <div className="data-table__meta">
                    {turn.businessId} / {turn.environment}
                  </div>
                </td>
                <td>
                  <span className={`status-pill status-pill--${turn.state}`}>{turn.state}</span>
                </td>
                <td>{turn.retryCount}</td>
                <td>
                  <strong>{turn.agentId}</strong>
                  <div className="data-table__meta">{turn.agentRevisionId}</div>
                </td>
                <td>{turn.updatedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
