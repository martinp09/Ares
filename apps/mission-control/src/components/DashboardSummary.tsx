import type { DashboardSummaryData } from "../lib/api";

interface DashboardSummaryProps {
  data: DashboardSummaryData;
}

const summaryCards: Array<{
  key: keyof Pick<
    DashboardSummaryData,
    | "approvalCount"
    | "activeRunCount"
    | "failedRunCount"
    | "activeAgentCount"
    | "unreadConversationCount"
    | "busyChannelCount"
  >;
  label: string;
}> = [
  { key: "approvalCount", label: "Approval queue" },
  { key: "activeRunCount", label: "Active runs" },
  { key: "failedRunCount", label: "Failed runs" },
  { key: "activeAgentCount", label: "Live agents" },
  { key: "unreadConversationCount", label: "Unread conversations" },
  { key: "busyChannelCount", label: "Busy channels" },
];

export function DashboardSummary({ data }: DashboardSummaryProps) {
  return (
    <section className="panel-stack" aria-label="Dashboard summary">
      <div className="summary-grid">
        {summaryCards.map((card) => (
          <article className="summary-card" key={card.key}>
            <p className="summary-card__label">{card.label}</p>
            <strong className="summary-card__value">{data[card.key]}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}
