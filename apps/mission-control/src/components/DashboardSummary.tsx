import type { DashboardSummaryData } from "../lib/api";

interface DashboardSummaryProps {
  data: DashboardSummaryData;
}

interface MetricCard {
  label: string;
  value: number;
  caption: string;
  glyph: string;
  tone: "orange" | "sky" | "green" | "amber";
  sparkline: number[];
}

function numberOrZero(value: number | undefined): number {
  return value ?? 0;
}

function MiniSparkline({ values, tone }: { values: number[]; tone: MetricCard["tone"] }) {
  const width = 132;
  const height = 42;
  const max = Math.max(...values, 1);
  const step = values.length > 1 ? width / (values.length - 1) : width;
  const points = values
    .map((value, index) => `${index * step},${height - (value / max) * (height - 8) - 4}`)
    .join(" ");

  return (
    <svg className={`metric-card__spark metric-card__spark--${tone}`} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Current metric shape">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <polygon points={`${points} ${width},${height} 0,${height}`} fill="currentColor" opacity="0.1" />
    </svg>
  );
}

export function DashboardSummary({ data }: DashboardSummaryProps) {
  const outboundReady = numberOrZero(data.outboundProbateSummary?.readyLeadCount ?? data.pendingLeadCount);
  const inboundPending = numberOrZero(data.inboundLeaseOptionSummary?.pendingLeadCount ?? data.pendingLeadCount);
  const replyReview = numberOrZero(data.inboundLeaseOptionSummary?.repliesNeedingReviewCount ?? data.repliesNeedingReviewCount);
  const unread = numberOrZero(data.unreadConversationCount);
  const approvals = numberOrZero(data.approvalCount);
  const opportunities = numberOrZero(data.opportunityPipelineSummary?.totalOpportunityCount ?? data.opportunityCount);
  const booked = numberOrZero(data.inboundLeaseOptionSummary?.bookedLeadCount ?? data.bookedLeadCount);
  const promoted = numberOrZero(data.recordInventorySummary?.promotedCount);

  const cards: MetricCard[] = [
    {
      label: "Ready leads",
      value: outboundReady + inboundPending,
      caption: "Probate queue + lease-option intake",
      glyph: "RL",
      tone: "orange",
      sparkline: [outboundReady, inboundPending, outboundReady + inboundPending],
    },
    {
      label: "Replies",
      value: Math.max(unread, replyReview),
      caption: "Human conversations waiting",
      glyph: "RP",
      tone: "sky",
      sparkline: [replyReview, unread, Math.max(unread, replyReview)],
    },
    {
      label: "Approvals",
      value: approvals,
      caption: "Approval-gated moves only",
      glyph: "OK",
      tone: "amber",
      sparkline: [0, Math.ceil(approvals / 2), approvals],
    },
    {
      label: "Opportunities",
      value: opportunities,
      caption: "Promoted records and booked leads",
      glyph: "DD",
      tone: "green",
      sparkline: [promoted, booked, opportunities],
    },
  ];

  return (
    <section className="metric-strip" aria-label="Dashboard KPI strip">
      {cards.map((card) => (
        <article className={`metric-card metric-card--${card.tone}`} key={card.label}>
          <div className="metric-card__header">
            <div>
              <p className="metric-card__label">{card.label}</p>
              <strong className="metric-card__value">{card.value}</strong>
            </div>
            <span className="metric-card__glyph" aria-hidden="true">{card.glyph}</span>
          </div>
          <MiniSparkline values={card.sparkline} tone={card.tone} />
          <span className="metric-card__caption">{card.caption}</span>
        </article>
      ))}
    </section>
  );
}
