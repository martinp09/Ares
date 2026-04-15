import type { AssetSummary } from "../lib/api";

interface ConnectLaterPanelProps {
  assets: AssetSummary[];
}

export function ConnectLaterPanel({ assets }: ConnectLaterPanelProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Operational assets</h3>
        <span>{assets.length} bindings</span>
      </div>
      <div className="list-stack">
        {assets.map((asset) => (
          <article className="list-card" key={asset.id}>
            <div className="list-card__row">
              <strong>{asset.name}</strong>
              <span className={`risk-pill risk-pill--${asset.status}`}>{asset.status}</span>
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>{asset.category}</span>
              <span>{asset.bindingTarget}</span>
            </div>
            <p className="list-card__body list-card__body--muted">Last change: {asset.updatedAt}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
