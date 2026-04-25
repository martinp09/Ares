import type { RecordsData } from "../lib/api";

interface RecordsPageProps {
  data: RecordsData;
}

function formatLabel(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function RecordsPage({ data }: RecordsPageProps) {
  const promotedRecords = data.records.filter((record) => record.promotionStatus === "promoted");

  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Records</h3>
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
          <p className="summary-card__label">Promoted</p>
          <strong className="summary-card__value">{data.kpis.promotedCount}</strong>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Open tasks</p>
          <strong className="summary-card__value">{data.kpis.openTaskCount}</strong>
        </article>
      </div>

      <div className="list-stack">
        {data.records.map((record) => (
          <article className="list-card" key={record.id} aria-label={`record-${record.id}`}>
            <div className="list-card__row">
              <strong>{record.displayName}</strong>
              <span>{formatLabel(record.recordStatus)}</span>
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>{formatLabel(record.source)}</span>
              <span>{record.propertyAddress ?? record.email ?? record.phone ?? "No contact anchor"}</span>
            </div>
            <p className="list-card__body">
              {record.promotionStatus === "promoted"
                ? `Pipeline: ${formatLabel(record.pipelineStage ?? "qualified_opportunity")}`
                : "Record inventory only"}
            </p>
            <div className="list-card__row list-card__row--muted">
              <span>{record.openTaskCount} open tasks</span>
              <span>{record.dataQualityScore}% data quality</span>
            </div>
          </article>
        ))}
      </div>

      {data.records.length === 0 ? <p className="panel-copy">No records match the current scope.</p> : null}
      {promotedRecords.length > 0 ? (
        <p className="panel-copy">{promotedRecords.length} records are linked downstream into opportunities.</p>
      ) : null}
    </section>
  );
}
