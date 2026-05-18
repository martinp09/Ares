import type { DashboardSummaryData } from "../lib/api";

interface DashboardSummaryProps {
  data: DashboardSummaryData;
}

function numberOrZero(value: number | undefined): number {
  return value ?? 0;
}

export function DashboardSummary({ data }: DashboardSummaryProps) {
  const outboundReady = numberOrZero(data.outboundProbateSummary?.readyLeadCount ?? data.pendingLeadCount);
  const inboundPending = numberOrZero(data.inboundLeaseOptionSummary?.pendingLeadCount ?? data.pendingLeadCount);
  const replyReview = numberOrZero(data.inboundLeaseOptionSummary?.repliesNeedingReviewCount ?? data.repliesNeedingReviewCount);
  const skipTrace = numberOrZero(data.recordInventorySummary?.needsSkipTraceCount);
  const openResearch = numberOrZero(
    data.recordInventorySummary?.openTaskCount ??
      data.outboundProbateSummary?.openTaskCount ??
      data.dueManualCallCount,
  );
  const opportunities = numberOrZero(data.opportunityPipelineSummary?.totalOpportunityCount ?? data.opportunityCount);
  const blocked = numberOrZero(data.recordInventorySummary?.suppressedCount) + numberOrZero(data.failedRunCount);

  const cards = [
    {
      label: "Hit list today",
      value: outboundReady + inboundPending,
      note: "Leads Martin can review first",
      tone: "hot",
    },
    {
      label: "Replies to review",
      value: Math.max(numberOrZero(data.unreadConversationCount), replyReview),
      note: "Human conversations waiting",
      tone: "warm",
    },
    {
      label: "Needs approval",
      value: numberOrZero(data.approvalCount),
      note: "Decisions before any action moves",
      tone: "approval",
    },
    {
      label: "Research / skiptrace",
      value: skipTrace + openResearch,
      note: "Missing info before contact",
      tone: "research",
    },
    {
      label: "Deals in motion",
      value: opportunities,
      note: "Opportunities past raw lead intake",
      tone: "deal",
    },
    {
      label: "Blocked / suppressions",
      value: blocked,
      note: "Do-not-touch or broken items",
      tone: "blocked",
    },
  ];

  return (
    <section className="action-desk" aria-label="Real estate action desk">
      {cards.map((card) => (
        <article className={`action-card action-card--${card.tone}`} key={card.label}>
          <p className="action-card__label">{card.label}</p>
          <strong className="action-card__value">{card.value}</strong>
          <span className="action-card__note">{card.note}</span>
        </article>
      ))}
    </section>
  );
}
