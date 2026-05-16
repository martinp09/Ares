import type { DealDeskData, DealRecordSummary, MissionControlDataSource } from "../lib/api";

interface DealDeskPageProps {
  data: DealDeskData;
  dataSource: MissionControlDataSource;
}

function formatLabel(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatStrategy(value: string | null | undefined): string {
  return formatLabel(value).toLowerCase();
}

function dealTitle(deal: DealRecordSummary): string {
  return deal.propertyAddress ?? deal.probateCaseNumber ?? deal.sourceLeadId ?? deal.id;
}

function fireCountForDeal(data: DealDeskData, dealId: string): number {
  return data.fireList.filter((item) => item.dealId === dealId).length;
}

export function DealDeskPage({ data, dataSource }: DealDeskPageProps) {
  const blockedCount = data.fireList.length;
  const noSendCount = data.deals.filter((deal) => deal.noSend || !deal.providerSendsEnabled).length;
  const laneCount = new Set(data.deals.map((deal) => deal.strategyLane)).size;

  return (
    <section className="crm-board deal-desk-page" aria-label="Deal desk">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Back Office Spine v0</p>
          <h3>Deal Desk Spine</h3>
        </div>
        <span>{dataSource === "api" ? "Live API" : "Fixture fallback"}</span>
      </div>

      <div className="crm-command-strip">
        <article className="metric-card">
          <span>Total deals</span>
          <strong>{data.deals.length}</strong>
          <p>Canonical Ares deal records in the current scope.</p>
        </article>
        <article className="metric-card">
          <span>Fire list</span>
          <strong>{blockedCount}</strong>
          <p>Risks, missing docs, due tasks, and provider gates.</p>
        </article>
        <article className="metric-card">
          <span>No-send locks</span>
          <strong>{noSendCount}</strong>
          <p>Provider actions stay disabled until explicit approval.</p>
        </article>
        <article className="metric-card">
          <span>Strategy lanes</span>
          <strong>{laneCount}</strong>
          <p>Curative title, lease option, cash, and creative finance split.</p>
        </article>
      </div>

      {data.deals.length === 0 ? (
        <article className="empty-state">
          <h4>No deals in this scope yet</h4>
          <p>Promote qualified leads into Ares deal records before working the back-office desk.</p>
        </article>
      ) : (
        <div className="deal-desk-grid" aria-label="Deal records">
          {data.deals.map((deal) => (
            <article className="opportunity-card" aria-label={dealTitle(deal)} key={deal.id}>
              <div className="opportunity-card__header">
                <div>
                  <h4>{dealTitle(deal)}</h4>
                  <p>{deal.county ? `${formatLabel(deal.county)} County` : "County pending"}</p>
                </div>
                <span className="status-pill">{formatLabel(deal.stage)}</span>
              </div>
              <dl className="opportunity-card__meta">
                <div>
                  <dt>Strategy</dt>
                  <dd>{formatStrategy(deal.strategyLane)}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{formatLabel(deal.sourceLane)}</dd>
                </div>
                <div>
                  <dt>Case</dt>
                  <dd>{deal.probateCaseNumber ?? "Not attached"}</dd>
                </div>
                <div>
                  <dt>Attention</dt>
                  <dd>{fireCountForDeal(data, deal.id)} fire-list item(s)</dd>
                </div>
              </dl>
              <p className="panel-copy">{deal.nextAction ?? "Review deal facts and choose the next operator action."}</p>
              <div className="opportunity-card__footer">
                <span className="status-pill muted">{deal.noSend || !deal.providerSendsEnabled ? "No-send locked" : "Provider gate open"}</span>
                <span>{deal.sourceLeadId ? `Lead ${deal.sourceLeadId}` : "Source lead pending"}</span>
              </div>
            </article>
          ))}
        </div>
      )}

      <section className="panel-stack" aria-label="Deal fire list">
        <div className="section-heading">
          <h3>Fire list</h3>
          <span>{blockedCount} open</span>
        </div>
        {data.fireList.length === 0 ? (
          <article className="empty-state">
            <h4>No fire-list items</h4>
            <p>There are no due tasks, missing documents, high risks, or provider gates in this scope.</p>
          </article>
        ) : (
          <div className="deal-desk-grid compact">
            {data.fireList.map((item, index) => (
              <article className="opportunity-card" key={`${item.dealId}-${item.sourceId ?? index}`}>
                <div className="opportunity-card__header">
                  <div>
                    <h4>{item.reason}</h4>
                    <p>{item.recommendedAction}</p>
                  </div>
                  <span className="status-pill">{formatLabel(item.severity)}</span>
                </div>
                <div className="opportunity-card__footer">
                  <span>{formatLabel(item.itemType)}</span>
                  <span>{item.actionEnabled ? "Action enabled" : "Operator review only"}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
