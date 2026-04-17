import type { OpportunityStageSummary } from "../lib/api";

interface PipelinePageProps {
  stages: OpportunityStageSummary[];
  totalCount?: number;
}

function formatStageLabel(stage: string): string {
  return stage
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function PipelinePage({ stages, totalCount = 0 }: PipelinePageProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Pipeline board</h3>
        <span>{totalCount} open opportunities</span>
      </div>

      <div className="summary-grid summary-grid--secondary">
        {stages.map((stage) => (
          <article className="summary-card summary-card--compact" key={stage.stage}>
            <p className="summary-card__label">{formatStageLabel(stage.stage)}</p>
            <strong className="summary-card__value">{stage.count}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}
