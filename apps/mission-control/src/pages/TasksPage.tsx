import type { TasksData } from "../lib/api";

interface TasksPageProps {
  data: TasksData;
}

export function TasksPage({ data }: TasksPageProps) {
  if (data.tasks.length === 0) {
    return (
      <section className="panel-stack">
        <div className="section-heading">
          <h3>Manual call queue</h3>
          <span>0 due</span>
        </div>
        <div className="list-card">
          <p className="list-card__body">No manual calls due</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Manual call queue</h3>
        <span>{data.dueCount} due</span>
      </div>
      <div className="list-stack">
        {data.tasks.map((task) => (
          <article className="list-card" key={task.threadId} aria-label={`manual-call-${task.threadId}`}>
            <div className="list-card__row">
              <strong>{task.leadName}</strong>
              <span>{task.manualCallDueAt}</span>
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>{task.bookingStatus}</span>
              <span>{task.sequenceStatus}</span>
            </div>
            <p className="list-card__body">{task.nextSequenceStep}</p>
            {task.replyNeedsReview ? <p className="list-card__body">Review required</p> : null}
            {task.recentReplyPreview ? <p className="list-card__body">{task.recentReplyPreview}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
