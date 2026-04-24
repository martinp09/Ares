import { DashboardSummary } from "../components/DashboardSummary";
import type { DashboardSummaryData } from "../lib/api";

interface DashboardPageProps {
  data: DashboardSummaryData;
}

export function DashboardPage({ data }: DashboardPageProps) {
  return (
    <div className="page-stack">
      <DashboardSummary data={data} />

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Operator summary</h3>
          <span>{data.updatedAt}</span>
        </div>
        <div className="summary-grid summary-grid--secondary">
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Recent completions</p>
            <strong className="summary-card__value">{data.recentCompletedCount}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Pending leads</p>
            <strong className="summary-card__value">{data.pendingLeadCount ?? 0}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Booked leads</p>
            <strong className="summary-card__value">{data.bookedLeadCount ?? 0}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Due manual calls</p>
            <strong className="summary-card__value">{data.dueManualCallCount ?? 0}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Replies needing review</p>
            <strong className="summary-card__value">{data.repliesNeedingReviewCount ?? 0}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Provider failures</p>
            <strong className="summary-card__value">{data.providerFailureTaskCount ?? 0}</strong>
          </article>
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">System status</p>
            <strong className="summary-card__value summary-card__value--status">{data.systemStatus}</strong>
          </article>
        </div>
      </section>
    </div>
  );
}
