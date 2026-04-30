import { useMemo, useState } from "react";

import type { OpportunityStageMoveRequest, OpportunityStageSummary } from "../lib/api";

interface PipelineActionState {
  opportunityId: string;
  status: "running" | "success" | "error";
  message: string;
}

interface PipelinePageProps {
  stages: OpportunityStageSummary[];
  totalCount?: number;
  onMoveStage: (opportunityId: string, request: OpportunityStageMoveRequest) => void;
  actionState: PipelineActionState | null;
}

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

export function PipelinePage({ stages, totalCount = 0, onMoveStage, actionState }: PipelinePageProps) {
  const stageOptions = useMemo(() => Array.from(new Set(stages.map((stage) => stage.stage))).sort(), [stages]);
  const [opportunityId, setOpportunityId] = useState("");
  const [targetStage, setTargetStage] = useState(stageOptions[0] ?? "qualified_opportunity");
  const [reason, setReason] = useState("");

  const trimmedOpportunityId = opportunityId.trim();
  const canMoveStage = trimmedOpportunityId.length > 0 && targetStage.length > 0 && actionState?.status !== "running";

  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Pipeline board</h3>
        <span>{totalCount} open opportunities</span>
      </div>

      <div className="summary-grid summary-grid--secondary">
        {stages.map((stage) => (
          <article className="summary-card summary-card--compact" key={`${stage.sourceLane}:${stage.stage}`}>
            <p className="summary-card__meta">{formatLaneLabel(stage.sourceLane)}</p>
            <p className="summary-card__label">{formatStageLabel(stage.stage)}</p>
            <strong className="summary-card__value">{stage.count}</strong>
          </article>
        ))}
      </div>

      <form
        className="surface-card form-grid"
        onSubmit={(event) => {
          event.preventDefault();
          if (!canMoveStage) {
            return;
          }
          onMoveStage(trimmedOpportunityId, {
            stage: targetStage,
            reason: reason.trim() || undefined,
            metadata: { surface: "mission-control-pipeline" },
          });
        }}
      >
        <div className="section-heading section-heading--compact">
          <h4>Move opportunity stage</h4>
          <span>Uses configured Phase 3 stage rules</span>
        </div>
        <label>
          Opportunity ID
          <input value={opportunityId} onChange={(event) => setOpportunityId(event.target.value)} placeholder="opp_..." />
        </label>
        <label>
          Target stage
          <select value={targetStage} onChange={(event) => setTargetStage(event.target.value)}>
            {stageOptions.map((stage) => (
              <option key={stage} value={stage}>
                {formatStageLabel(stage)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Move reason
          <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Why this stage move is valid" />
        </label>
        <button type="submit" disabled={!canMoveStage}>
          Move stage
        </button>
        {actionState ? (
          <p className={`status-text status-text--${actionState.status}`}>{actionState.message}</p>
        ) : null}
      </form>
    </section>
  );
}
