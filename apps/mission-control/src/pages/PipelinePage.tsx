import { useEffect, useMemo, useState } from "react";

import type {
  CrmRecordSummary,
  OpportunityRecordSummary,
  OpportunityStageMoveRequest,
  OpportunityStageSummary,
} from "../lib/api";

interface PipelineActionState {
  opportunityId: string;
  status: "running" | "success" | "error";
  message: string;
}

interface PipelinePageProps {
  stages: OpportunityStageSummary[];
  opportunities: OpportunityRecordSummary[];
  records: CrmRecordSummary[];
  totalCount?: number;
  onMoveStage: (opportunityId: string, request: OpportunityStageMoveRequest) => void;
  actionState: PipelineActionState | null;
}

const DEFAULT_STAGE_ORDER = [
  "qualified_opportunity",
  "offer_path_selected",
  "under_negotiation",
  "contract_sent",
  "contract_signed",
  "title_open",
  "curative_review",
  "dispo_ready",
  "closed",
  "dead",
];

function formatStageLabel(stage: string): string {
  return stage
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatLaneLabel(sourceLane: string): string {
  return sourceLane
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function metadataString(opportunity: OpportunityRecordSummary, key: string): string | null {
  const value = opportunity.metadata[key];
  if (value === null || value === undefined) {
    return null;
  }
  return String(value);
}

function opportunityValue(opportunity: OpportunityRecordSummary): string {
  const rawValue =
    metadataString(opportunity, "estimated_value") ??
    metadataString(opportunity, "value") ??
    metadataString(opportunity, "offer_value");
  const numericValue = rawValue ? Number(rawValue) : Number.NaN;
  if (Number.isFinite(numericValue) && numericValue > 0) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(numericValue);
  }
  return "Value pending";
}

function opportunityNextAction(opportunity: OpportunityRecordSummary): string {
  return (
    metadataString(opportunity, "next_action") ??
    metadataString(opportunity, "nextBestAction") ??
    (opportunity.stage === "qualified_opportunity" ? "Select offer path" : "Review stage requirements")
  );
}

function matchOpportunityRecord(opportunity: OpportunityRecordSummary, records: CrmRecordSummary[]): CrmRecordSummary | undefined {
  return records.find((record) => {
    if (record.opportunityId && record.opportunityId === opportunity.id) {
      return true;
    }
    if (opportunity.leadId && record.sourceLeadId === opportunity.leadId) {
      return true;
    }
    if (opportunity.contactId && record.sourceContactId === opportunity.contactId) {
      return true;
    }
    return false;
  });
}

function sortStages(stages: string[]): string[] {
  return [...stages].sort((left, right) => {
    const leftIndex = DEFAULT_STAGE_ORDER.indexOf(left);
    const rightIndex = DEFAULT_STAGE_ORDER.indexOf(right);
    if (leftIndex === -1 && rightIndex === -1) {
      return left.localeCompare(right);
    }
    if (leftIndex === -1) {
      return 1;
    }
    if (rightIndex === -1) {
      return -1;
    }
    return leftIndex - rightIndex;
  });
}

export function PipelinePage({
  stages,
  opportunities,
  records,
  totalCount = 0,
  onMoveStage,
  actionState,
}: PipelinePageProps) {
  const stageOptions = useMemo(
    () => sortStages(Array.from(new Set([...DEFAULT_STAGE_ORDER, ...stages.map((stage) => stage.stage), ...opportunities.map((opportunity) => opportunity.stage)]))),
    [opportunities, stages],
  );
  const lanes = useMemo(() => Array.from(new Set(opportunities.map((opportunity) => opportunity.sourceLane))).sort(), [opportunities]);
  const [activeLane, setActiveLane] = useState<string>("all");
  const visibleOpportunities = useMemo(
    () => (activeLane === "all" ? opportunities : opportunities.filter((opportunity) => opportunity.sourceLane === activeLane)),
    [activeLane, opportunities],
  );
  const boardStages = DEFAULT_STAGE_ORDER;
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<string | null>(opportunities[0]?.id ?? null);
  const [targetStage, setTargetStage] = useState(opportunities[0]?.stage ?? stageOptions[0] ?? "qualified_opportunity");
  const [reason, setReason] = useState("");

  const selectedOpportunity = visibleOpportunities.find((opportunity) => opportunity.id === selectedOpportunityId) ?? visibleOpportunities[0] ?? null;
  const selectedRecord = selectedOpportunity ? matchOpportunityRecord(selectedOpportunity, records) : undefined;
  const currentStageIndex = selectedOpportunity ? DEFAULT_STAGE_ORDER.indexOf(selectedOpportunity.stage) : -1;
  const isActionRunning = actionState?.status === "running";
  const canMoveStage = Boolean(
    selectedOpportunity &&
      targetStage.length > 0 &&
      targetStage !== selectedOpportunity.stage &&
      !isActionRunning,
  );
  const titleOpenCount = visibleOpportunities.filter((opportunity) => opportunity.titleStatus !== "not_open").length;
  const dispoReadyCount = visibleOpportunities.filter((opportunity) => opportunity.dispoStatus === "ready").length;
  const staleCount = visibleOpportunities.filter((opportunity) => opportunity.tcStatus === "blocked" || opportunity.dispoStatus === "blocked").length;
  const promotedRecordCount = records.filter((record) => record.promotionStatus === "promoted").length;
  const skipTraceCount = records.filter((record) => record.recordStatus === "needs_skip_trace").length;
  const contactedCount = records.filter((record) => record.hasEmail || record.hasPhone).length;

  useEffect(() => {
    if ((!selectedOpportunityId || !visibleOpportunities.some((opportunity) => opportunity.id === selectedOpportunityId)) && visibleOpportunities[0]) {
      setSelectedOpportunityId(visibleOpportunities[0].id);
      setTargetStage(visibleOpportunities[0].stage);
    }
  }, [selectedOpportunityId, visibleOpportunities]);

  return (
    <section className="crm-board">
      <div className="crm-hero-panel">
        <div className="crm-hero-panel__copy">
          <span>Ares CRM</span>
          <h3>Pipeline Command Center</h3>
          <p>Records, opportunities, stage movement, title posture, and next actions in one operational surface.</p>
        </div>
        <div className="crm-hero-panel__stats" aria-label="CRM portfolio metrics">
          <article>
            <strong>{records.length}</strong>
            <span>records</span>
          </article>
          <article>
            <strong>{promotedRecordCount}</strong>
            <span>promoted</span>
          </article>
          <article>
            <strong>{skipTraceCount}</strong>
            <span>skip trace</span>
          </article>
          <article>
            <strong>{contactedCount}</strong>
            <span>contactable</span>
          </article>
        </div>
      </div>

      <div className="crm-lane-tabs" aria-label="Source lane filters">
        <button
          type="button"
          className={`crm-lane-tab${activeLane === "all" ? " crm-lane-tab--active" : ""}`}
          onClick={() => setActiveLane("all")}
        >
          <span>All lanes</span>
          <strong>{opportunities.length}</strong>
        </button>
        {lanes.map((lane) => (
          <button
            type="button"
            className={`crm-lane-tab${activeLane === lane ? " crm-lane-tab--active" : ""}`}
            key={lane}
            onClick={() => setActiveLane(lane)}
          >
            <span>{formatLaneLabel(lane)}</span>
            <strong>{opportunities.filter((opportunity) => opportunity.sourceLane === lane).length}</strong>
          </button>
        ))}
      </div>

      <div className="crm-command-strip" aria-label="Pipeline command metrics">
        <article>
          <span>Total pipeline</span>
          <strong>{visibleOpportunities.length || totalCount}</strong>
          <small>open opportunities</small>
        </article>
        <article>
          <span>Title active</span>
          <strong>{titleOpenCount}</strong>
          <small>title or curative lanes</small>
        </article>
        <article>
          <span>Dispo ready</span>
          <strong>{dispoReadyCount}</strong>
          <small>ready for disposition</small>
        </article>
        <article>
          <span>Blocked</span>
          <strong>{staleCount}</strong>
          <small>needs operator review</small>
        </article>
      </div>

      <div className="crm-workspace">
        <div className="pipeline-board" aria-label="Opportunity pipeline board">
          {boardStages.map((stage) => {
            const stageOpportunities = visibleOpportunities.filter((opportunity) => opportunity.stage === stage);
            const stageSummaryCount = stages
              .filter((summary) => summary.stage === stage && (activeLane === "all" || summary.sourceLane === activeLane))
              .reduce((count, summary) => count + summary.count, 0);
            return (
              <section className="pipeline-column" key={stage} aria-label={`${formatStageLabel(stage)} stage`}>
                <div className="pipeline-column__header">
                  <div>
                    <h3>{formatStageLabel(stage)}</h3>
                    <span>{stageSummaryCount || stageOpportunities.length} opportunities</span>
                  </div>
                  <strong>{stageOpportunities.length}</strong>
                </div>
                <div className="pipeline-column__cards">
                  {stageOpportunities.map((opportunity) => {
                    const record = matchOpportunityRecord(opportunity, records);
                    const isSelected = selectedOpportunity?.id === opportunity.id;
                    return (
                      <button
                        type="button"
                        className={`opportunity-card${isSelected ? " opportunity-card--active" : ""}`}
                        key={opportunity.id}
                        onClick={() => {
                          setSelectedOpportunityId(opportunity.id);
                          setTargetStage(opportunity.stage);
                        }}
                      >
                        <span className="opportunity-card__lane">{formatLaneLabel(opportunity.sourceLane)}</span>
                        <strong>{record?.displayName ?? opportunity.id}</strong>
                        <span>{record?.propertyAddress ?? record?.mailingAddress ?? opportunity.leadId ?? opportunity.contactId}</span>
                        <div className="opportunity-card__meta">
                          <span>{opportunityValue(opportunity)}</span>
                          <span>Title: {formatStageLabel(opportunity.titleStatus)}</span>
                        </div>
                        <small>{opportunityNextAction(opportunity)}</small>
                      </button>
                    );
                  })}
                  {stageOpportunities.length === 0 ? (
                    <div className="pipeline-column__empty">
                      <span>Empty: {formatStageLabel(stage)}</span>
                      <p>Ready for the next qualified handoff.</p>
                    </div>
                  ) : null}
                </div>
              </section>
            );
          })}
        </div>

        <aside className="opportunity-drawer" aria-label="Opportunity detail">
          {selectedOpportunity ? (
            <>
              <div className="opportunity-drawer__header">
                <span>{formatLaneLabel(selectedOpportunity.sourceLane)}</span>
                <h3>{selectedRecord?.displayName ?? selectedOpportunity.id}</h3>
                <p>{selectedRecord?.propertyAddress ?? selectedRecord?.mailingAddress ?? selectedOpportunity.leadId ?? selectedOpportunity.contactId}</p>
              </div>

              <div className="opportunity-stage-rail" aria-label="Stage progress">
                {DEFAULT_STAGE_ORDER.map((stage, index) => (
                  <span
                    key={stage}
                    className={`opportunity-stage-dot${index <= currentStageIndex ? " opportunity-stage-dot--active" : ""}`}
                    title={formatStageLabel(stage)}
                  />
                ))}
              </div>

              <dl className="opportunity-detail-grid">
                <div>
                  <dt>Current stage</dt>
                  <dd>{formatStageLabel(selectedOpportunity.stage)}</dd>
                </div>
                <div>
                  <dt>Value</dt>
                  <dd>{opportunityValue(selectedOpportunity)}</dd>
                </div>
                <div>
                  <dt>Title</dt>
                  <dd>{formatStageLabel(selectedOpportunity.titleStatus)}</dd>
                </div>
                <div>
                  <dt>Transaction</dt>
                  <dd>{formatStageLabel(selectedOpportunity.tcStatus)}</dd>
                </div>
                <div>
                  <dt>Dispo</dt>
                  <dd>{formatStageLabel(selectedOpportunity.dispoStatus)}</dd>
                </div>
                <div>
                  <dt>Owner</dt>
                  <dd>{selectedRecord?.ownerName ?? "Unassigned"}</dd>
                </div>
              </dl>

              <form
                className="opportunity-action-panel"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!selectedOpportunity || !canMoveStage) {
                    return;
                  }
                  onMoveStage(selectedOpportunity.id, {
                    stage: targetStage,
                    reason: reason.trim() || undefined,
                    metadata: { surface: "mission-control-pipeline-board" },
                  });
                }}
              >
                <label>
                  Target stage
                  <select value={targetStage} onChange={(event) => setTargetStage(event.target.value)}>
                    {stageOptions.map((stage) => (
                      <option key={stage} value={stage}>
                        Move to {formatStageLabel(stage)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Move reason
                  <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Why this stage move is valid" />
                </label>
                <button type="submit" disabled={!canMoveStage}>
                  Move selected opportunity
                </button>
                {actionState?.opportunityId === selectedOpportunity.id ? (
                  <p className={`status-text status-text--${actionState.status}`}>{actionState.message}</p>
                ) : null}
              </form>

              <div className="opportunity-next-actions">
                <h4>Next actions</h4>
                <p>{opportunityNextAction(selectedOpportunity)}</p>
                <p>{selectedRecord?.openTaskCount ?? 0} open record tasks attached to this opportunity.</p>
              </div>
            </>
          ) : (
            <p className="panel-copy">No opportunities match the current CRM filters.</p>
          )}
        </aside>
      </div>
    </section>
  );
}
