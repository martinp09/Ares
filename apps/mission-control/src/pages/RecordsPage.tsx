import { useMemo, useState } from "react";

import type { CrmRecordSummary, RecordsData } from "../lib/api";

interface RecordsPageProps {
  data: RecordsData;
}

type RecordTabId = "all" | "needs_skip_trace" | "marketable" | "suppressed" | "promoted" | "incomplete";

interface RecordTab {
  id: RecordTabId;
  label: string;
  matches: (record: CrmRecordSummary) => boolean;
}

const RECORD_TABS: RecordTab[] = [
  { id: "all", label: "All", matches: () => true },
  { id: "needs_skip_trace", label: "Needs Skip Trace", matches: (record) => record.recordStatus === "needs_skip_trace" },
  { id: "marketable", label: "Marketable", matches: (record) => record.lifecycleStatus === "marketable" },
  { id: "suppressed", label: "Suppressed", matches: (record) => record.recordStatus === "suppressed" },
  { id: "promoted", label: "Promoted", matches: (record) => record.promotionStatus === "promoted" },
  { id: "incomplete", label: "Incomplete", matches: (record) => record.lifecycleStatus === "incomplete" },
];

function formatLabel(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function recordAnchor(record: CrmRecordSummary): string {
  return record.propertyAddress ?? record.mailingAddress ?? record.email ?? record.phone ?? "No contact anchor";
}

function contactabilityLabel(record: CrmRecordSummary): string {
  if (record.hasPhone && record.hasEmail) {
    return "Phone + email";
  }
  if (record.hasPhone) {
    return "Phone ready";
  }
  if (record.hasEmail) {
    return "Email only";
  }
  return "No phone/email";
}

function qualityLabel(score: number): string {
  if (score >= 80) {
    return "High quality";
  }
  if (score >= 50) {
    return "Needs cleanup";
  }
  return "Incomplete";
}

export function RecordsPage({ data }: RecordsPageProps) {
  const [activeTab, setActiveTab] = useState<RecordTabId>("all");
  const promotedRecords = data.records.filter((record) => record.promotionStatus === "promoted");
  const tabCounts = useMemo(
    () =>
      RECORD_TABS.reduce<Record<RecordTabId, number>>(
        (counts, tab) => ({ ...counts, [tab.id]: data.records.filter(tab.matches).length }),
        {
          all: 0,
          needs_skip_trace: 0,
          marketable: 0,
          suppressed: 0,
          promoted: 0,
          incomplete: 0,
        },
      ),
    [data.records],
  );
  const selectedTab = RECORD_TABS.find((tab) => tab.id === activeTab) ?? RECORD_TABS[0];
  const visibleRecords = data.records.filter(selectedTab.matches);

  return (
    <section className="panel-stack">
      <div className="section-heading">
        <div>
          <h3>Records</h3>
          <p className="panel-copy">Canonical prospect inventory before promotion into active opportunities.</p>
        </div>
        <span>{data.kpis.totalCount} inventory records</span>
      </div>

      <div className="summary-grid summary-grid--secondary">
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Total records</p>
          <strong className="summary-card__value">{data.kpis.totalCount}</strong>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Needs skip trace</p>
          <strong className="summary-card__value">{data.kpis.needsSkipTraceCount}</strong>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Marketable / active</p>
          <strong className="summary-card__value">{data.kpis.activeCount}</strong>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">No phone</p>
          <strong className="summary-card__value">{data.kpis.noPhoneCount}</strong>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Promoted</p>
          <strong className="summary-card__value">{data.kpis.promotedCount}</strong>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Open tasks</p>
          <strong className="summary-card__value">{data.kpis.openTaskCount}</strong>
        </article>
      </div>

      <div className="record-tabs" aria-label="Record filters">
        {RECORD_TABS.map((tab) => (
          <button
            type="button"
            key={tab.id}
            className={`record-tab${activeTab === tab.id ? " record-tab--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span>{tab.label}</span>
            <strong>{tabCounts[tab.id]}</strong>
          </button>
        ))}
      </div>

      <div className="list-stack">
        {visibleRecords.map((record) => (
          <article className="list-card" key={record.id} aria-label={`record-${record.id}`}>
            <div className="list-card__row">
              <strong>{record.displayName}</strong>
              <span className="status-pill">{formatLabel(record.recordStatus)}</span>
            </div>
            <div className="record-badge-row" aria-label={`record-${record.id}-badges`}>
              <span className="status-badge">{formatLabel(record.recordType)}</span>
              <span className="status-badge">{formatLabel(record.source)}</span>
              <span className="status-badge">{contactabilityLabel(record)}</span>
              <span className="status-badge">{qualityLabel(record.dataQualityScore)}</span>
              {record.promotionStatus === "promoted" ? <span className="status-badge status-badge--amber">Promoted</span> : null}
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>{recordAnchor(record)}</span>
              <span>{record.assignedTo ? `Assigned to ${record.assignedTo}` : "Unassigned"}</span>
            </div>
            <p className="list-card__body">
              {record.promotionStatus === "promoted"
                ? `Pipeline: ${formatLabel(record.pipelineStage ?? "qualified_opportunity")}`
                : "Read-only inventory row — action buttons land after the Records command API."}
            </p>
            <div className="list-card__row list-card__row--muted">
              <span>{record.openTaskCount} open tasks</span>
              <span>{record.dataQualityScore}% data quality</span>
            </div>
          </article>
        ))}
      </div>

      {visibleRecords.length === 0 ? <p className="panel-copy">No records match the {selectedTab.label} view.</p> : null}
      {promotedRecords.length > 0 ? (
        <p className="panel-copy">{promotedRecords.length} records are linked downstream into opportunities.</p>
      ) : null}
    </section>
  );
}
