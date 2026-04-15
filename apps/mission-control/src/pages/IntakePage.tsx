const workflowSteps = [
  {
    label: "Submit lead",
    status: "done",
    copy: "Form lands in the queue immediately and stays visible.",
  },
  {
    label: "Book appointment",
    status: "done",
    copy: "Operator can move the lead into a scheduled slot without leaving the cockpit.",
  },
  {
    label: "Send confirmation SMS",
    status: "queued",
    copy: "Confirmation stays trackable if delivery stalls or retries are needed.",
  },
  {
    label: "Schedule reminder SMS",
    status: "queued",
    copy: "One reminder is enough for this slice; keep it auditable and visible.",
  },
] as const;

const intakeMetrics = [
  { label: "Submission visibility", value: "Immediate" },
  { label: "Appointment booking", value: "Operator-driven" },
  { label: "Confirmation SMS", value: "Queued" },
  { label: "Reminder SMS", value: "Scheduled" },
] as const;

const intakeCheckpoints = [
  {
    milestone: "Form submission arrives",
    status: "completed",
    detail: "The lead lands in the operator queue the moment the form is submitted.",
  },
  {
    milestone: "Lead appears in operator UI",
    status: "completed",
    detail: "The incoming lead stays visible in Mission Control instead of disappearing into logs.",
  },
  {
    milestone: "Appointment can be booked",
    status: "completed",
    detail: "Operators can move the lead straight into a booked appointment from the cockpit.",
  },
  {
    milestone: "Confirmation SMS goes out",
    status: "queued",
    detail: "The confirmation text is queued and stays visible if delivery stalls.",
  },
  {
    milestone: "One reminder SMS is scheduled",
    status: "queued",
    detail: "The single reminder job is tracked separately so it does not vanish into the void.",
  },
  {
    milestone: "Status and failures stay visible",
    status: "in_progress",
    detail: "If delivery breaks, the failure needs to stay loud enough for an operator to act on it.",
  },
] as const;

export function IntakePage() {
  return (
    <div className="page-stack intake-stack">
      <section className="intake-hero" aria-label="Mission Control happy path">
        <div className="intake-hero__top">
          <div>
            <p className="intake-hero__eyebrow">Mission Control / Intake</p>
            <h3 className="intake-hero__title">Submission to appointment, with the ugly parts still visible.</h3>
            <p className="intake-hero__copy">
              Fixture-backed on this machine. The real backend cutover stays on the MacBook. No white surfaces, no
              fake product marketing nonsense.
            </p>
          </div>
          <span className="status-badge status-badge--amber">Happy path locked</span>
        </div>

        <div className="workflow-line">
          <div className="workflow-line__track">
            {workflowSteps.map((step) => (
              <article className={`workflow-line__step workflow-line__step--${step.status}`} key={step.label}>
                <div>
                  <div className="workflow-line__label">{step.label}</div>
                  <div className="workflow-line__meta">{step.status}</div>
                </div>
                <span className="intake-chip">{step.status}</span>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="panel-stack" aria-label="Mission Control metrics">
        <div className="section-heading">
          <h3>Execution metrics</h3>
          <span>Flagship flow health</span>
        </div>
        <div className="intake-metric-grid">
          {intakeMetrics.map((metric) => (
            <article className="intake-metric-card" key={metric.label}>
              <div className="intake-metric-card__top">
                <p className="summary-card__label">{metric.label}</p>
              </div>
              <strong className="intake-metric-card__value">{metric.value}</strong>
            </article>
          ))}
        </div>
        <p className="intake-note">
          This screen stays the flagship. If this path feels clear, the rest of Mission Control can be tuned around it
          instead of pretending to be important.
        </p>
      </section>

      <section className="panel-stack" aria-label="Execution checkpoints">
        <div className="section-heading">
          <h3>Execution checkpoints</h3>
          <span>Operator-visible</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Checkpoint</th>
              <th scope="col">State</th>
              <th scope="col">Why it matters</th>
            </tr>
          </thead>
          <tbody>
            {intakeCheckpoints.map((checkpoint) => (
              <tr key={checkpoint.milestone}>
                <td>{checkpoint.milestone}</td>
                <td>
                  <span className={`status-pill status-pill--${checkpoint.status}`}>{checkpoint.status}</span>
                </td>
                <td>{checkpoint.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="intake-callout" aria-label="Failure watchpoints">
        <div className="intake-callout__top">
          <div>
            <h3 className="intake-callout__title">Failure watchpoints</h3>
            <p className="intake-callout__body">Keep the ugly bits loud enough that an operator can act on them.</p>
          </div>
          <span className="status-badge">Watch mode</span>
        </div>
        <ul className="detail-list">
          <li>Duplicate submissions must stay obvious.</li>
          <li>SMS delivery failures should surface in the cockpit, not in a dead queue.</li>
          <li>The reminder job should remain auditable until the local backend wiring is finished.</li>
        </ul>
      </section>
    </div>
  );
}
