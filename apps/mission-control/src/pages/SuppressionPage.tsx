import type { DashboardSummaryData, InboxData, RunSummary, TasksData } from "../lib/api";

interface SuppressionPageProps {
  dashboard: DashboardSummaryData;
  inbox: InboxData;
  runs: RunSummary[];
  tasks: TasksData;
}

function lower(value: string | undefined | null): string {
  return String(value ?? "").toLowerCase();
}

export function SuppressionPage({ dashboard, inbox, runs, tasks }: SuppressionPageProps) {
  const reviewThreads = inbox.conversations.filter((conversation) => {
    const stage = lower(conversation.stage);
    const sequenceState = lower(conversation.sequenceState);
    return conversation.replyNeedsReview || sequenceState.includes("suppress") || stage.includes("suppression");
  });
  const failedRuns = runs.filter((run) => run.status === "failed");
  const exceptionTasks = tasks.tasks.filter(
    (task) => task.replyNeedsReview || lower(task.sequenceStatus).includes("pause") || lower(task.bookingStatus).includes("booked")
  );

  return (
    <section className="panel-stack" aria-label="suppression workspace">
      <div className="section-heading">
        <h3>Suppression / Exceptions</h3>
        <span>{dashboard.repliesNeedingReviewCount ?? reviewThreads.length} reviews</span>
      </div>

      <div className="stats-grid">
        <article className="metric-card">
          <span className="metric-card__label">Replies needing review</span>
          <strong>{dashboard.repliesNeedingReviewCount ?? reviewThreads.length}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Failed runs</span>
          <strong>{dashboard.failedRunCount}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Suppression watch</span>
          <strong>{dashboard.repliesNeedingReviewCount ?? 0}</strong>
        </article>
      </div>

      <div className="panel-stack">
        <div className="section-heading">
          <h3>Review queue</h3>
          <span>{reviewThreads.length} leads</span>
        </div>
        <div className="list-stack">
          {reviewThreads.length === 0 ? (
            <article className="list-card">
              <p className="list-card__body">No leads currently need suppression review.</p>
            </article>
          ) : (
            reviewThreads.map((conversation) => (
              <article className="list-card" key={conversation.id} aria-label={`suppression-${conversation.id}`}>
                <div className="list-card__row">
                  <strong>{conversation.leadName}</strong>
                  <span>{conversation.lastActivityAt}</span>
                </div>
                <div className="list-card__row list-card__row--muted">
                  <span>{conversation.stage}</span>
                  <span>{conversation.sequenceState}</span>
                </div>
                <p className="list-card__body">{conversation.lastMessage}</p>
                {conversation.replyNeedsReview ? <p className="list-card__body">Reply needs review</p> : null}
              </article>
            ))
          )}
        </div>
      </div>

      <div className="panel-stack">
        <div className="section-heading">
          <h3>Exceptions</h3>
          <span>{failedRuns.length} runs / {exceptionTasks.length} tasks</span>
        </div>
        <div className="list-stack">
          {failedRuns.length === 0 && exceptionTasks.length === 0 ? (
            <article className="list-card">
              <p className="list-card__body">No exceptions are currently blocking the lane.</p>
            </article>
          ) : null}
          {failedRuns.map((run) => (
            <article className="list-card" key={run.id} aria-label={`failed-run-${run.id}`}>
              <div className="list-card__row">
                <strong>{run.commandType}</strong>
                <span>{run.updatedAt}</span>
              </div>
              <div className="list-card__row list-card__row--muted">
                <span>{run.status}</span>
                <span>{run.businessId}</span>
              </div>
              <p className="list-card__body">{run.summary}</p>
            </article>
          ))}
          {exceptionTasks.map((task) => (
            <article className="list-card" key={task.threadId} aria-label={`exception-task-${task.threadId}`}>
              <div className="list-card__row">
                <strong>{task.leadName}</strong>
                <span>{task.manualCallDueAt}</span>
              </div>
              <div className="list-card__row list-card__row--muted">
                <span>{task.bookingStatus}</span>
                <span>{task.sequenceStatus}</span>
              </div>
              <p className="list-card__body">{task.nextSequenceStep}</p>
              {task.replyNeedsReview ? <p className="list-card__body">Reply needs review</p> : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
