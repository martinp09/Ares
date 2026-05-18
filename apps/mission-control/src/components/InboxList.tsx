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
        <div>
          <h3>Conversation Desk</h3>
          <p>Chatwoot-style seller inbox · Ares-native source of truth</p>
        </div>
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
                <span>{conversation.replyNeedsReview ? "needs Martin" : conversation.owner}</span>
                <span>{conversation.unreadCount} unread</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
