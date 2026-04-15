import type { ConversationSummary } from "../lib/api";

interface InboxListProps {
  conversations: ConversationSummary[];
  selectedConversationId: string;
  onSelectConversation: (conversationId: string) => void;
}

export function InboxList({
  conversations,
  selectedConversationId,
  onSelectConversation,
}: InboxListProps) {
  return (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>Inbox queue</h3>
        <span>{conversations.length} threads</span>
      </div>
      <div className="list-stack">
        {conversations.map((conversation) => {
          const isActive = conversation.id === selectedConversationId;
          return (
            <button
              key={conversation.id}
              className={`list-card${isActive ? " list-card--active" : ""}`}
              onClick={() => onSelectConversation(conversation.id)}
              type="button"
            >
              <div className="list-card__row">
                <strong>{conversation.leadName}</strong>
                <span>{conversation.lastActivityAt}</span>
              </div>
              <div className="list-card__row list-card__row--muted">
                <span>{conversation.channel}</span>
                <span>{conversation.stage}</span>
              </div>
              <p className="list-card__body">{conversation.lastMessage}</p>
              <div className="list-card__row list-card__row--muted">
                <span>{conversation.sequenceState}</span>
                <span>{conversation.unreadCount} unread</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
