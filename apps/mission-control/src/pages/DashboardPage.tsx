import { DashboardSummary } from "../components/DashboardSummary";
import type { DashboardSummaryData } from "../lib/api";

interface DashboardPageProps {
  data: DashboardSummaryData;
}

interface BarDatum {
  label: string;
  value: number;
  helper: string;
  tone: "orange" | "sky" | "green" | "amber" | "purple" | "slate";
}

interface FunnelDatum {
  label: string;
  value: number;
  helper: string;
}

function numberOrZero(value: number | undefined): number {
  return value ?? 0;
}

function formatPercent(numerator: number, denominator: number): string {
  if (denominator <= 0) return "0%";
  return `${Math.round((numerator / denominator) * 100)}%`;
}

function maxOf(values: number[]): number {
  return Math.max(...values, 1);
}

function HorizontalBarChart({ data, ariaLabel }: { data: BarDatum[]; ariaLabel: string }) {
  const max = maxOf(data.map((item) => item.value));

  return (
    <div className="analytics-bars" role="img" aria-label={ariaLabel}>
      {data.map((item) => {
        const width = Math.max(item.value > 0 ? 8 : 0, Math.round((item.value / max) * 100));
        return (
          <div className="analytics-bars__row" key={item.label}>
            <div className="analytics-bars__meta">
              <strong>{item.label}</strong>
              <span>{item.helper}</span>
            </div>
            <div className="analytics-bars__track" aria-hidden="true">
              <span className={`analytics-bars__fill analytics-bars__fill--${item.tone}`} style={{ width: `${width}%` }} />
            </div>
            <span className="analytics-bars__value">{item.value}</span>
          </div>
        );
      })}
    </div>
  );
}

function FunnelChart({ data }: { data: FunnelDatum[] }) {
  const max = maxOf(data.map((item) => item.value));

  return (
    <div className="funnel-chart" role="img" aria-label="Acquisition funnel from inventory to deals">
      {data.map((item, index) => {
        const width = Math.max(item.value > 0 ? 18 : 0, Math.round((item.value / max) * 100));
        return (
          <div className="funnel-chart__row" key={item.label}>
            <span className="funnel-chart__label">{item.label}</span>
            <div className="funnel-chart__track" aria-hidden="true">
              <span className="funnel-chart__fill" style={{ width: `${width}%`, opacity: 0.92 - index * 0.09 }}>
                {item.value}
              </span>
            </div>
            <span className="funnel-chart__helper">{item.helper}</span>
          </div>
        );
      })}
    </div>
  );
}

function DonutChart({ ready, research, blocked }: { ready: number; research: number; blocked: number }) {
  const total = ready + research + blocked;
  const readyPct = total > 0 ? (ready / total) * 100 : 0;
  const researchPct = total > 0 ? ((ready + research) / total) * 100 : 0;
  const background = total > 0
    ? `conic-gradient(#22c55e 0 ${readyPct}%, #ff8c00 ${readyPct}% ${researchPct}%, #64748b ${researchPct}% 100%)`
    : "rgba(100, 116, 139, 0.22)";

  return (
    <div className="donut-readiness">
      <div className="donut-readiness__chart" style={{ background }} aria-hidden="true">
        <span>{formatPercent(ready, total)}</span>
        <small>ready</small>
      </div>
      <div className="donut-readiness__legend" aria-label="Contact readiness mix">
        <span><i className="legend-dot legend-dot--green" />{ready} ready</span>
        <span><i className="legend-dot legend-dot--orange" />{research} research</span>
        <span><i className="legend-dot legend-dot--slate" />{blocked} blocked</span>
      </div>
    </div>
  );
}

function SegmentCard({ title, eyebrow, items }: { title: string; eyebrow: string; items: { label: string; value: number }[] }) {
  return (
    <article className="segment-card">
      <div className="section-heading">
        <h3>{title}</h3>
        <span>{eyebrow}</span>
      </div>
      <dl className="segment-card__metrics">
        {items.map((item) => (
          <div key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

export function DashboardPage({ data }: DashboardPageProps) {
  const outbound = data.outboundProbateSummary;
  const inbound = data.inboundLeaseOptionSummary;
  const records = data.recordInventorySummary;
  const pipeline = data.opportunityPipelineSummary;

  const probateReady = numberOrZero(outbound?.readyLeadCount ?? data.pendingLeadCount);
  const probateActive = numberOrZero(outbound?.activeLeadCount);
  const probateInterested = numberOrZero(outbound?.interestedLeadCount);
  const probateSuppressed = numberOrZero(outbound?.suppressedLeadCount);
  const probateTasks = numberOrZero(outbound?.openTaskCount ?? data.dueManualCallCount);

  const leasePending = numberOrZero(inbound?.pendingLeadCount ?? data.pendingLeadCount);
  const leaseBooked = numberOrZero(inbound?.bookedLeadCount ?? data.bookedLeadCount);
  const leaseFollowUp = numberOrZero(inbound?.activeNonBookerEnrollmentCount ?? data.activeNonBookerEnrollmentCount);
  const leaseCalls = numberOrZero(inbound?.dueManualCallCount ?? data.dueManualCallCount);
  const leaseReplies = numberOrZero(inbound?.repliesNeedingReviewCount ?? data.repliesNeedingReviewCount);

  const inventoryTotal = numberOrZero(records?.totalCount);
  const inventoryActive = numberOrZero(records?.activeCount);
  const needsSkiptrace = numberOrZero(records?.needsSkipTraceCount);
  const openResearch = numberOrZero(records?.openTaskCount ?? probateTasks);
  const suppressed = numberOrZero(records?.suppressedCount) + probateSuppressed;
  const promoted = numberOrZero(records?.promotedCount);
  const opportunities = numberOrZero(pipeline?.totalOpportunityCount ?? data.opportunityCount);
  const blocked = suppressed + numberOrZero(data.failedRunCount);
  const readyTotal = probateReady + leasePending;
  const engagedTotal = probateInterested + leaseReplies;
  const dealTotal = opportunities + leaseBooked;

  const laneBars: BarDatum[] = [
    { label: "Probate ready", value: probateReady, helper: "curative-title / tax lane", tone: "orange" },
    { label: "Probate interested", value: probateInterested, helper: "seller signal captured", tone: "green" },
    { label: "Lease-option pending", value: leasePending, helper: "inbound leads waiting", tone: "sky" },
    { label: "Lease-option booked", value: leaseBooked, helper: "consults scheduled", tone: "purple" },
    { label: "Deal opportunities", value: opportunities, helper: "promoted into deal desk", tone: "amber" },
  ];

  const funnel: FunnelDatum[] = [
    { label: "Inventory", value: inventoryTotal || probateActive + leasePending + needsSkiptrace + suppressed, helper: "all known records" },
    { label: "Active", value: inventoryActive || probateActive + leasePending, helper: "still workable" },
    { label: "Ready", value: readyTotal, helper: "can review now" },
    { label: "Engaged", value: engagedTotal, helper: "reply / interest signal" },
    { label: "Deals", value: dealTotal, helper: "booked or promoted" },
  ];

  const blockerBars: BarDatum[] = [
    { label: "Needs skiptrace", value: needsSkiptrace, helper: "no clean phone/contact path", tone: "purple" },
    { label: "Open research", value: openResearch, helper: "title, property, or task evidence", tone: "amber" },
    { label: "Suppressed", value: suppressed, helper: "do-not-touch records", tone: "slate" },
    { label: "Broken / blocked", value: numberOrZero(data.failedRunCount), helper: "stuck items only", tone: "sky" },
  ];

  return (
    <div className="page-stack dashboard-analytics-page">
      <section className="dashboard-title-card" aria-label="Dashboard analytics overview">
        <div>
          <p className="dashboard-title-card__eyebrow">Overview</p>
          <h3>Dashboard analytics</h3>
          <p>
            Segmented, chart-first view of Ares real-estate work: lead flow, contact readiness,
            blocker mix, and deal movement. Admin/backend controls stay out of this overview.
          </p>
        </div>
        <div className="dashboard-title-card__status">
          <span>Safety posture</span>
          <strong>No-send locked</strong>
          <small>Updated: {data.updatedAt}</small>
        </div>
      </section>

      <DashboardSummary data={data} />

      <section className="analytics-grid analytics-grid--primary" aria-label="Dashboard charts">
        <article className="analytics-panel analytics-panel--wide">
          <div className="panel-header-row">
            <div>
              <p className="panel-kicker">Lead flow</p>
              <h3>Lane performance</h3>
            </div>
            <span className="panel-pill">Current snapshot</span>
          </div>
          <HorizontalBarChart data={laneBars} ariaLabel="Lead flow by real-estate lane" />
        </article>

        <article className="analytics-panel">
          <div className="panel-header-row">
            <div>
              <p className="panel-kicker">Readiness</p>
              <h3>Contact mix</h3>
            </div>
            <span className="panel-pill">{formatPercent(readyTotal + promoted, readyTotal + promoted + needsSkiptrace + openResearch + blocked)} ready</span>
          </div>
          <DonutChart ready={readyTotal + promoted} research={needsSkiptrace + openResearch} blocked={blocked} />
        </article>
      </section>

      <section className="analytics-grid analytics-grid--secondary" aria-label="Funnel and blockers">
        <article className="analytics-panel">
          <div className="panel-header-row">
            <div>
              <p className="panel-kicker">Pipeline</p>
              <h3>Acquisition funnel</h3>
            </div>
            <span className="panel-pill">{dealTotal} deals</span>
          </div>
          <FunnelChart data={funnel} />
        </article>

        <article className="analytics-panel">
          <div className="panel-header-row">
            <div>
              <p className="panel-kicker">Blockers</p>
              <h3>What is stopping movement?</h3>
            </div>
            <span className="panel-pill">{needsSkiptrace + openResearch + blocked} items</span>
          </div>
          <HorizontalBarChart data={blockerBars} ariaLabel="Current blocker mix" />
        </article>
      </section>

      <section className="segment-grid" aria-label="Segmented operating view">
        <SegmentCard
          title="Acquisition lanes"
          eyebrow="source flow"
          items={[
            { label: "Probate active", value: probateActive },
            { label: "Probate ready", value: probateReady },
            { label: "Lease pending", value: leasePending },
            { label: "Interested", value: probateInterested },
          ]}
        />
        <SegmentCard
          title="Follow-up desk"
          eyebrow="human review"
          items={[
            { label: "Replies", value: Math.max(numberOrZero(data.unreadConversationCount), leaseReplies) },
            { label: "Manual calls", value: leaseCalls },
            { label: "Approvals", value: numberOrZero(data.approvalCount) },
            { label: "Follow-up", value: leaseFollowUp },
          ]}
        />
        <SegmentCard
          title="Deal movement"
          eyebrow="pipeline"
          items={[
            { label: "Opportunities", value: opportunities },
            { label: "Promoted", value: promoted },
            { label: "Booked", value: leaseBooked },
            { label: "Skiptrace", value: needsSkiptrace },
          ]}
        />
      </section>
    </div>
  );
}
