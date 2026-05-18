import { useEffect, useMemo, useState } from "react";

import type { CrmRecordSavedView, CrmRecordStatus, CrmRecordSummary, RecordsData } from "../lib/api";

export type RecordsPageMode = "inventory" | "hot" | "property" | "owner" | "skiptrace" | "tax-title";

interface RecordsPageProps {
  data: RecordsData;
  mode?: RecordsPageMode;
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

interface RecordsModeConfig {
  title: string;
  copy: string;
  segmentLabel: string;
  emptyLabel: string;
  defaultTab: RecordTabId;
  matches: (record: CrmRecordSummary) => boolean;
}

const RECORD_TABS: RecordTab[] = [
  { id: "all", label: "All", matches: () => true },
  { id: "needs_skip_trace", label: "Needs Skip Trace", matches: (record) => record.recordStatus === "needs_skip_trace" || !record.hasPhone },
  {
    id: "marketable",
    label: "Marketable",
    matches: (record) => record.lifecycleStatus === "marketable" || record.recordStatus === "marketable" || (record.hasPhone && record.dataQualityScore >= 70),
  },
  { id: "suppressed", label: "Suppressed", matches: (record) => record.recordStatus === "suppressed" },
  { id: "promoted", label: "Promoted", matches: (record) => record.promotionStatus === "promoted" },
  {
    id: "incomplete",
    label: "Incomplete",
    matches: (record) => record.lifecycleStatus === "incomplete" || !record.propertyAddress || (!record.hasPhone && !record.hasEmail),
  },
];

const RECORDS_MODE_CONFIG: Record<RecordsPageMode, RecordsModeConfig> = {
  inventory: {
    title: "Records",
    copy: "Canonical prospect inventory before promotion into active opportunities.",
    segmentLabel: "inventory records",
    emptyLabel: "records",
    defaultTab: "all",
    matches: () => true,
  },
  hot: {
    title: "Hot lead cards",
    copy: "The most actionable owners and properties: contactable, high-quality, or already promoted toward a deal lane.",
    segmentLabel: "hot records",
    emptyLabel: "hot lead records",
    defaultTab: "marketable",
    matches: (record) => record.promotionStatus === "promoted" || record.recordStatus === "marketable" || (record.hasPhone && record.dataQualityScore >= 70),
  },
  property: {
    title: "Property cards",
    copy: "Property-first record cards for address, county/source clues, pipeline posture, and missing research.",
    segmentLabel: "property cards",
    emptyLabel: "property cards",
    defaultTab: "all",
    matches: (record) => Boolean(record.propertyAddress || record.mailingAddress),
  },
  owner: {
    title: "Owner cards",
    copy: "Owner-first record cards for contact readiness, assignment, source identity, and follow-up state.",
    segmentLabel: "owner cards",
    emptyLabel: "owner cards",
    defaultTab: "all",
    matches: (record) => Boolean(record.ownerName || record.displayName || record.phone || record.email),
  },
  skiptrace: {
    title: "Skip trace queue",
    copy: "Records missing phone coverage or explicitly marked for skip trace before seller contact.",
    segmentLabel: "skip trace records",
    emptyLabel: "skip trace records",
    defaultTab: "needs_skip_trace",
    matches: (record) => record.recordStatus === "needs_skip_trace" || !record.hasPhone,
  },
  "tax-title": {
    title: "Tax / title desk",
    copy: "Property records that need tax, probate, title, or curative-title review before Martin spends time on outreach.",
    segmentLabel: "tax/title records",
    emptyLabel: "tax/title records",
    defaultTab: "all",
    matches: (record) => {
      const source = `${record.source} ${record.pipelineStage ?? ""} ${record.recordType}`.toLowerCase();
      return source.includes("probate") || source.includes("tax") || source.includes("title") || record.promotionStatus === "promoted";
    },
  },
};

export function recordsForMode(records: CrmRecordSummary[], mode: RecordsPageMode): CrmRecordSummary[] {
  return records.filter(RECORDS_MODE_CONFIG[mode].matches);
}

export function countRecordsForMode(records: CrmRecordSummary[], mode: RecordsPageMode): number {
  return recordsForMode(records, mode).length;
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

function missingInfo(record: CrmRecordSummary): string[] {
  const missing: string[] = [];
  if (!record.hasPhone) {
    missing.push("Phone missing — queue skip trace before seller call work.");
  }
  if (!record.propertyAddress) {
    missing.push("Property address missing — match owner to an address before valuing the lead.");
  }
  if (record.dataQualityScore < 70) {
    missing.push(`Data quality is ${record.dataQualityScore}% — verify identity, property, and contact facts.`);
  }
  if (!record.sourceLeadId && !record.sourceContactId) {
    missing.push("Source identity missing — promotion stays gated until lead/contact identity is exposed.");
  }
  if (record.recordStatus === "suppressed") {
    missing.push("Suppression review required before this record can re-enter a work queue.");
  }
  if (missing.length === 0) {
    missing.push("Contact-ready from the record view; outreach still requires Martin's explicit strategy/copy approval.");
  }
  return missing;
}

function detailRows(record: CrmRecordSummary): Array<{ label: string; value: string }> {
  return [
    { label: "Record ID", value: record.id },
    { label: "Record type", value: formatLabel(record.recordType) },
    { label: "Source", value: formatLabel(record.source) },
    { label: "Lifecycle", value: formatLabel(record.lifecycleStatus) },
    { label: "Record status", value: formatLabel(record.recordStatus) },
    { label: "Promotion", value: formatLabel(record.promotionStatus) },
    { label: "Pipeline", value: record.pipelineStage ? formatLabel(record.pipelineStage) : "Not promoted" },
    { label: "Opportunity", value: record.opportunityId ?? "Not linked" },
  ];
}

export function RecordsPage({ data, mode = "inventory", actionState, onRecordStatusChange, onRecordSuppress, onRecordPromote }: RecordsPageProps) {
  const modeConfig = RECORDS_MODE_CONFIG[mode];
  const defaultSavedView = data.savedViews.find((view) => view.isDefault) ?? data.savedViews[0];
  const [activeSavedViewId, setActiveSavedViewId] = useState<string | null>(defaultSavedView?.id ?? null);
  const [activeTab, setActiveTab] = useState<RecordTabId>(modeConfig.defaultTab);
  const [activeRecordId, setActiveRecordId] = useState<string | null>(null);
  const [selectedRecordIds, setSelectedRecordIds] = useState<Set<string>>(() => new Set());
  const [isBulkActionRunning, setIsBulkActionRunning] = useState(false);
  const scopedRecords = useMemo(() => recordsForMode(data.records, mode), [data.records, mode]);
  const promotedRecords = scopedRecords.filter((record) => record.promotionStatus === "promoted");
  const tabCounts = useMemo(
    () =>
      RECORD_TABS.reduce<Record<RecordTabId, number>>(
        (counts, tab) => ({ ...counts, [tab.id]: scopedRecords.filter(tab.matches).length }),
        {
          all: 0,
          needs_skip_trace: 0,
          marketable: 0,
          suppressed: 0,
          promoted: 0,
          incomplete: 0,
        },
      ),
    [scopedRecords],
  );
  const selectedTab = RECORD_TABS.find((tab) => tab.id === activeTab) ?? RECORD_TABS[0];
  const selectedSavedView = data.savedViews.find((view) => view.id === activeSavedViewId) ?? defaultSavedView;
  const savedViewRecords = selectedSavedView ? scopedRecords.filter((record) => savedViewMatches(record, selectedSavedView)) : scopedRecords;
  const visibleRecords = savedViewRecords.filter(selectedTab.matches);
  const visibleRecordIds = useMemo(() => new Set(visibleRecords.map((record) => record.id)), [visibleRecords]);
  const activeRecord = visibleRecords.find((record) => record.id === activeRecordId) ?? visibleRecords[0] ?? null;
  const selectedVisibleRecords = visibleRecords.filter((record) => selectedRecordIds.has(record.id));
  const displayedSegmentCount = mode === "inventory" ? data.kpis.totalCount : scopedRecords.length;
  const canRunRecordActions = Boolean(onRecordStatusChange && onRecordSuppress);
  const isActionRunning = actionState?.status === "running" || isBulkActionRunning;
  const canRunBulkRecordActions = canRunRecordActions && selectedVisibleRecords.length > 0 && !isActionRunning;
  const allVisibleRecordsSelected = visibleRecords.length > 0 && visibleRecords.every((record) => selectedRecordIds.has(record.id));
  const canPromoteRecord = (record: CrmRecordSummary): boolean =>
    Boolean(onRecordPromote && record.promotionStatus !== "promoted" && (record.sourceLeadId || record.sourceContactId));

  useEffect(() => {
    setActiveTab(modeConfig.defaultTab);
    setActiveRecordId(null);
    setSelectedRecordIds(new Set());
  }, [mode, modeConfig.defaultTab]);

  useEffect(() => {
    if (defaultSavedView && !data.savedViews.some((view) => view.id === activeSavedViewId)) {
      setActiveSavedViewId(defaultSavedView.id);
    }
  }, [activeSavedViewId, data.savedViews, defaultSavedView]);

  useEffect(() => {
    if (!activeRecordId || !visibleRecordIds.has(activeRecordId)) {
      setActiveRecordId(visibleRecords[0]?.id ?? null);
    }
  }, [activeRecordId, visibleRecordIds, visibleRecords]);

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
    <section className="panel-stack records-page">
      <div className="section-heading">
        <div>
          <h3>{modeConfig.title}</h3>
          <p className="panel-copy">{modeConfig.copy}</p>
        </div>
        <span>{displayedSegmentCount} {modeConfig.segmentLabel}</span>
      </div>

      <div className="summary-grid summary-grid--secondary">
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Total records</p>
          <strong className="summary-card__value">{data.kpis.totalCount}</strong>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">This segment</p>
          <strong className="summary-card__value">{scopedRecords.length}</strong>
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
            aria-label={`${view.name} ${scopedRecords.filter((record) => savedViewMatches(record, view)).length}`}
            className={`record-tab${selectedSavedView?.id === view.id ? " record-tab--active" : ""}`}
            onClick={() => {
              setActiveSavedViewId(view.id);
              setActiveTab("all");
            }}
          >
            <span>{view.name}</span>
            <strong>{scopedRecords.filter((record) => savedViewMatches(record, view)).length}</strong>
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

      <div className="records-workbench">
        <div className="list-stack record-card-list" aria-label="Record card list">
          {visibleRecords.map((record) => (
            <article className={`list-card record-list-card${activeRecord?.id === record.id ? " record-list-card--active" : ""}`} key={record.id} aria-label={`record-${record.id}`}>
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
                  onClick={() => setActiveRecordId(record.id)}
                >
                  Open record card
                </button>
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

        <aside className="record-detail-card" aria-label="Record detail card">
          {activeRecord ? (
            <>
              <p className="workspace-header__eyebrow">Record card</p>
              <div className="record-detail-card__header">
                <div>
                  <h4>{activeRecord.displayName}</h4>
                  <p>{recordAnchor(activeRecord)}</p>
                </div>
                <span className="status-pill">{qualityLabel(activeRecord.dataQualityScore)}</span>
              </div>

              <div className="record-detail-grid">
                <article>
                  <span>Property</span>
                  <strong>{activeRecord.propertyAddress ?? "Address missing"}</strong>
                  <small>{activeRecord.mailingAddress ? `Mailing: ${activeRecord.mailingAddress}` : "Mailing address not captured"}</small>
                </article>
                <article>
                  <span>Owner</span>
                  <strong>{activeRecord.ownerName ?? activeRecord.displayName}</strong>
                  <small>{activeRecord.assignedTo ? `Assigned to ${activeRecord.assignedTo}` : "No operator assigned"}</small>
                </article>
                <article>
                  <span>Contact</span>
                  <strong>{contactabilityLabel(activeRecord)}</strong>
                  <small>{activeRecord.phone ?? activeRecord.email ?? "No phone or email on card"}</small>
                </article>
                <article>
                  <span>Movement</span>
                  <strong>{activeRecord.pipelineStage ? formatLabel(activeRecord.pipelineStage) : formatLabel(activeRecord.promotionStatus)}</strong>
                  <small>{activeRecord.openTaskCount} open task(s)</small>
                </article>
              </div>

              <div className="record-detail-sections">
                <section>
                  <h5>Property / owner details</h5>
                  <dl className="record-detail-list">
                    {detailRows(activeRecord).map((row) => (
                      <div key={row.label}>
                        <dt>{row.label}</dt>
                        <dd>{row.value}</dd>
                      </div>
                    ))}
                  </dl>
                </section>

                <section>
                  <h5>Missing before contact</h5>
                  <ul className="record-missing-list">
                    {missingInfo(activeRecord).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>

                <section>
                  <h5>Safety gate</h5>
                  <p>No seller outreach, paid skiptrace, CRM write, or provider send is launched from this card without explicit approval.</p>
                </section>
              </div>
            </>
          ) : (
            <p className="panel-copy">No record card is available for this segment yet.</p>
          )}
        </aside>
      </div>

      {visibleRecords.length === 0 ? <p className="panel-copy">No {modeConfig.emptyLabel} match the {selectedSavedView?.name ?? selectedTab.label} view.</p> : null}
      {promotedRecords.length > 0 ? (
        <p className="panel-copy">{promotedRecords.length} records in this segment are linked downstream into opportunities.</p>
      ) : null}
    </section>
  );
}
