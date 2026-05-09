import { useMemo, useState } from "react";

import type { CrmRecordSavedView, CrmRecordStatus, CrmRecordSummary, RecordsData } from "../lib/api";

interface RecordsPageProps {
  data: RecordsData;
  actionState?: RecordActionState | null;
  onRecordStatusChange?: (record: CrmRecordSummary, status: CrmRecordStatus, reason: string) => Promise<void> | void;
  onRecordSuppress?: (record: CrmRecordSummary, reason: string) => Promise<void> | void;
  onRecordPromote?: (record: CrmRecordSummary) => Promise<void> | void;
}

interface RecordActionState {
  recordId: string;
  status: "running" | "success" | "error";
  message: string;
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

function savedViewMatches(record: CrmRecordSummary, savedView: CrmRecordSavedView): boolean {
  return Object.entries(savedView.filters).every(([key, value]) => {
    if (key === "record_status") {
      return record.recordStatus === value;
    }
    if (key === "lifecycle_status") {
      return record.lifecycleStatus === value;
    }
    if (key === "promotion_status") {
      return record.promotionStatus === value;
    }
    if (key === "record_type") {
      return record.recordType === value;
    }
    if (key === "has_phone") {
      return record.hasPhone === value;
    }
    return true;
  });
}

export function RecordsPage({ data, actionState, onRecordStatusChange, onRecordSuppress, onRecordPromote }: RecordsPageProps) {
  const defaultSavedView = data.savedViews.find((view) => view.isDefault) ?? data.savedViews[0];
  const [activeSavedViewId, setActiveSavedViewId] = useState<string | null>(defaultSavedView?.id ?? null);
  const [activeTab, setActiveTab] = useState<RecordTabId>("all");
  const [selectedRecordIds, setSelectedRecordIds] = useState<Set<string>>(() => new Set());
  const [isBulkActionRunning, setIsBulkActionRunning] = useState(false);
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
  const selectedSavedView = data.savedViews.find((view) => view.id === activeSavedViewId) ?? defaultSavedView;
  const savedViewRecords = selectedSavedView ? data.records.filter((record) => savedViewMatches(record, selectedSavedView)) : data.records;
  const visibleRecords = savedViewRecords.filter(selectedTab.matches);
  const visibleRecordIds = useMemo(() => new Set(visibleRecords.map((record) => record.id)), [visibleRecords]);
  const selectedVisibleRecords = visibleRecords.filter((record) => selectedRecordIds.has(record.id));
  const canRunRecordActions = Boolean(onRecordStatusChange && onRecordSuppress);
  const isActionRunning = actionState?.status === "running" || isBulkActionRunning;
  const canRunBulkRecordActions = canRunRecordActions && selectedVisibleRecords.length > 0 && !isActionRunning;
  const allVisibleRecordsSelected = visibleRecords.length > 0 && visibleRecords.every((record) => selectedRecordIds.has(record.id));
  const canPromoteRecord = (record: CrmRecordSummary): boolean =>
    Boolean(onRecordPromote && record.promotionStatus !== "promoted" && (record.sourceLeadId || record.sourceContactId));

  const toggleSelectedRecord = (recordId: string): void => {
    setSelectedRecordIds((current) => {
      const next = new Set(current);
      if (next.has(recordId)) {
        next.delete(recordId);
      } else {
        next.add(recordId);
      }
      return next;
    });
  };

  const toggleVisibleRecords = (): void => {
    setSelectedRecordIds((current) => {
      const next = new Set(current);
      if (allVisibleRecordsSelected) {
        for (const recordId of visibleRecordIds) {
          next.delete(recordId);
        }
      } else {
        for (const recordId of visibleRecordIds) {
          next.add(recordId);
        }
      }
      return next;
    });
  };

  const runBulkStatusChange = async (status: CrmRecordStatus, reason: string): Promise<void> => {
    setIsBulkActionRunning(true);
    try {
      for (const record of selectedVisibleRecords) {
        await onRecordStatusChange?.(record, status, reason);
      }
    } finally {
      setIsBulkActionRunning(false);
    }
  };

  const runBulkSuppress = async (): Promise<void> => {
    setIsBulkActionRunning(true);
    try {
      for (const record of selectedVisibleRecords) {
        await onRecordSuppress?.(record, "Bulk suppressed selected visible records from Mission Control Records workspace");
      }
    } finally {
      setIsBulkActionRunning(false);
    }
  };

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

      <div className="record-tabs" aria-label="Saved record views">
        {data.savedViews.map((view) => (
          <button
            type="button"
            key={view.id}
            aria-label={`${view.name} ${data.records.filter((record) => savedViewMatches(record, view)).length}`}
            className={`record-tab${selectedSavedView?.id === view.id ? " record-tab--active" : ""}`}
            onClick={() => {
              setActiveSavedViewId(view.id);
              setActiveTab("all");
            }}
          >
            <span>{view.name}</span>
            <strong>{data.records.filter((record) => savedViewMatches(record, view)).length}</strong>
          </button>
        ))}
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

      <div className="record-bulk-actions" aria-label="Record bulk actions">
        <label className="record-select-all">
          <input
            type="checkbox"
            checked={allVisibleRecordsSelected}
            disabled={visibleRecords.length === 0 || isActionRunning}
            onChange={toggleVisibleRecords}
          />
          <span>{selectedVisibleRecords.length} selected</span>
        </label>
        <button
          type="button"
          className="button button--ghost"
          disabled={!canRunBulkRecordActions}
          onClick={() => {
            void runBulkStatusChange("marketable", "Operator bulk-marked selected visible records marketable from Mission Control");
          }}
        >
          Mark marketable selected
        </button>
        <button
          type="button"
          className="button button--ghost"
          disabled={!canRunBulkRecordActions}
          onClick={() => {
            void runBulkStatusChange("needs_skip_trace", "Operator bulk-marked selected visible records for skip trace from Mission Control");
          }}
        >
          Needs skip trace selected
        </button>
        <button
          type="button"
          className="button button--ghost"
          disabled={!canRunBulkRecordActions}
          onClick={() => {
            void runBulkSuppress();
          }}
        >
          Suppress selected
        </button>
      </div>

      <div className="list-stack">
        {visibleRecords.map((record) => (
          <article className="list-card" key={record.id} aria-label={`record-${record.id}`}>
            <div className="list-card__row">
              <label className="record-select-row">
                <input
                  type="checkbox"
                  checked={selectedRecordIds.has(record.id)}
                  disabled={isActionRunning}
                  aria-label={`Select ${record.displayName}`}
                  onChange={() => toggleSelectedRecord(record.id)}
                />
                <strong>{record.displayName}</strong>
              </label>
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
                : record.sourceLeadId || record.sourceContactId
                  ? "Record actions call the CRM command API; promotion is available for rows with source identity."
                  : "Record actions call the CRM command API; promotion is gated until source identity is exposed to the row."}
            </p>
            <div className="record-badge-row" aria-label={`record-${record.id}-actions`}>
              <button
                type="button"
                className="button button--ghost"
                disabled={!canRunRecordActions || actionState?.status === "running" || record.recordStatus === "marketable"}
                onClick={() => onRecordStatusChange?.(record, "marketable", "Operator marked record marketable from Mission Control")}
              >
                Mark marketable
              </button>
              <button
                type="button"
                className="button button--ghost"
                disabled={!canRunRecordActions || actionState?.status === "running" || record.recordStatus === "needs_skip_trace"}
                onClick={() => onRecordStatusChange?.(record, "needs_skip_trace", "Operator marked record for skip trace from Mission Control")}
              >
                Needs skip trace
              </button>
              <button
                type="button"
                className="button button--ghost"
                disabled={!canRunRecordActions || actionState?.status === "running" || record.recordStatus === "suppressed"}
                onClick={() => onRecordSuppress?.(record, "Suppressed from Mission Control Records workspace")}
              >
                Suppress
              </button>
              <button
                type="button"
                className="button button--ghost"
                disabled={actionState?.status === "running" || !canPromoteRecord(record)}
                title={canPromoteRecord(record) ? "Promote this record into the opportunity pipeline." : "Promotion requires source lead/contact identity on the Records row."}
                onClick={() => onRecordPromote?.(record)}
              >
                {canPromoteRecord(record) ? "Promote" : "Promote gated"}
              </button>
              {actionState?.recordId === record.id ? <span className={`status-badge status-badge--${actionState.status === "error" ? "red" : "amber"}`}>{actionState.message}</span> : null}
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>{record.openTaskCount} open tasks</span>
              <span>{record.dataQualityScore}% data quality</span>
            </div>
          </article>
        ))}
      </div>

      {visibleRecords.length === 0 ? <p className="panel-copy">No records match the {selectedSavedView?.name ?? selectedTab.label} view.</p> : null}
      {promotedRecords.length > 0 ? (
        <p className="panel-copy">{promotedRecords.length} records are linked downstream into opportunities.</p>
      ) : null}
    </section>
  );
}
