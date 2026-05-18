import { DashboardSummary } from "../components/DashboardSummary";
import type { DashboardSummaryData } from "../lib/api";

interface DashboardPageProps {
  data: DashboardSummaryData;
}

function numberOrZero(value: number | undefined): number {
  return value ?? 0;
}

function buildTodayActions(data: DashboardSummaryData) {
  const outboundReady = numberOrZero(data.outboundProbateSummary?.readyLeadCount ?? data.pendingLeadCount);
  const inboundPending = numberOrZero(data.inboundLeaseOptionSummary?.pendingLeadCount ?? data.pendingLeadCount);
  const replies = numberOrZero(data.inboundLeaseOptionSummary?.repliesNeedingReviewCount ?? data.repliesNeedingReviewCount);
  const manualCalls = numberOrZero(data.inboundLeaseOptionSummary?.dueManualCallCount ?? data.dueManualCallCount);
  const approvals = numberOrZero(data.approvalCount);
  const skiptrace = numberOrZero(data.recordInventorySummary?.needsSkipTraceCount);
  const blocked = numberOrZero(data.recordInventorySummary?.suppressedCount) + numberOrZero(data.failedRunCount);

  return [
    {
      title: "Contact-ready lead desk",
      count: outboundReady + inboundPending,
      label: "leads",
      copy: "Start here: probate leads ready for review plus inbound lease-option submissions.",
    },
    {
      title: "Messages needing Martin",
      count: Math.max(replies, numberOrZero(data.unreadConversationCount)),
      label: "threads",
      copy: "Review seller replies and decide what the Chief of Staff should do next.",
    },
    {
      title: "Approval queue",
      count: approvals,
      label: "decisions",
      copy: "Nothing should send or mutate providers until these are approved intentionally.",
    },
    {
      title: "Research / skiptrace bench",
      count: skiptrace + manualCalls,
      label: "items",
      copy: "Missing phone, property, title, or follow-up evidence before a lead can move.",
    },
    {
      title: "Blocked or dead",
      count: blocked,
      label: "items",
      copy: "Suppressed records, failed runs, and anything the operator should avoid today.",
    },
  ];
}

export function DashboardPage({ data }: DashboardPageProps) {
  const outbound = data.outboundProbateSummary;
  const inbound = data.inboundLeaseOptionSummary;
  const records = data.recordInventorySummary;
  const pipeline = data.opportunityPipelineSummary;
  const todayActions = buildTodayActions(data);

  return (
    <div className="page-stack dashboard-operator-page">
      <section className="dashboard-hero" aria-label="Today command briefing">
        <div>
          <p className="dashboard-hero__eyebrow">Today</p>
          <h3>What should Martin work first?</h3>
          <p>
            A human-readable lead desk for real-estate action: hot leads, replies, missing info,
            blocked records, and deal movement. Backend plumbing stays out of the primary dashboard.
          </p>
        </div>
        <div className="dashboard-hero__status">
          <span>Safety</span>
          <strong>No-send locked</strong>
          <small>Updated: {data.updatedAt}</small>
        </div>
      </section>

      <DashboardSummary data={data} />

      <section className="operator-kanban" aria-label="Daily action board">
        {todayActions.map((action, index) => (
          <article className="operator-kanban__card" key={action.title}>
            <div className="operator-kanban__topline">
              <span>0{index + 1}</span>
              <strong>{action.title}</strong>
            </div>
            <div className="operator-kanban__metric">
              <strong>{action.count}</strong>
              <span>{action.label}</span>
            </div>
            <p>{action.copy}</p>
          </article>
        ))}
      </section>

      <section className="lane-grid" aria-label="Real estate lane overview">
        <article className="lane-card lane-card--probate">
          <div className="section-heading">
            <h3>Probate / tax title lane</h3>
            <span>Outbound</span>
          </div>
          <dl className="lane-card__metrics">
            <div><dt>Ready</dt><dd>{numberOrZero(outbound?.readyLeadCount ?? data.pendingLeadCount)}</dd></div>
            <div><dt>Interested</dt><dd>{numberOrZero(outbound?.interestedLeadCount)}</dd></div>
            <div><dt>Needs task</dt><dd>{numberOrZero(outbound?.openTaskCount ?? data.dueManualCallCount)}</dd></div>
            <div><dt>Suppressed</dt><dd>{numberOrZero(outbound?.suppressedLeadCount)}</dd></div>
          </dl>
        </article>

        <article className="lane-card lane-card--lease">
          <div className="section-heading">
            <h3>Lease-option lane</h3>
            <span>Inbound</span>
          </div>
          <dl className="lane-card__metrics">
            <div><dt>Pending</dt><dd>{numberOrZero(inbound?.pendingLeadCount ?? data.pendingLeadCount)}</dd></div>
            <div><dt>Booked</dt><dd>{numberOrZero(inbound?.bookedLeadCount ?? data.bookedLeadCount)}</dd></div>
            <div><dt>Follow-up</dt><dd>{numberOrZero(inbound?.activeNonBookerEnrollmentCount ?? data.activeNonBookerEnrollmentCount)}</dd></div>
            <div><dt>Replies</dt><dd>{numberOrZero(inbound?.repliesNeedingReviewCount ?? data.repliesNeedingReviewCount)}</dd></div>
          </dl>
        </article>

        <article className="lane-card lane-card--pipeline">
          <div className="section-heading">
            <h3>Deal desk</h3>
            <span>Pipeline</span>
          </div>
          <dl className="lane-card__metrics">
            <div><dt>Opportunities</dt><dd>{numberOrZero(pipeline?.totalOpportunityCount ?? data.opportunityCount)}</dd></div>
            <div><dt>Records</dt><dd>{numberOrZero(records?.totalCount)}</dd></div>
            <div><dt>Promoted</dt><dd>{numberOrZero(records?.promotedCount)}</dd></div>
            <div><dt>Skiptrace</dt><dd>{numberOrZero(records?.needsSkipTraceCount)}</dd></div>
          </dl>
        </article>
      </section>
    </div>
  );
}
