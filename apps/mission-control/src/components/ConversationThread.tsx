import type { SelectedThread } from "../lib/api";

interface ConversationThreadProps {
  thread: SelectedThread;
}

export function ConversationThread({ thread }: ConversationThreadProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <div>
          <h3>{thread.leadName}</h3>
          <p>{thread.company}</p>
        </div>
        <span>{thread.stage}</span>
      </div>
      <div className="thread-stack">
        {thread.messages.map((message) => (
          <article className={`thread-message thread-message--${message.direction}`} key={message.id}>
            <div className="list-card__row">
              <strong>{message.author}</strong>
              <span>{message.timestamp}</span>
            </div>
            <p>{message.body}</p>
            <span className="thread-message__status">{message.status}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
