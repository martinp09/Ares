import { ConversationThread } from "../components/ConversationThread";
import { InboxList } from "../components/InboxList";
import type { InboxData } from "../lib/api";

interface InboxPageProps {
  data: InboxData;
  selectedConversationId: string;
  onSelectConversation: (conversationId: string) => void;
}

export function InboxPage({
  data,
  selectedConversationId,
  onSelectConversation,
}: InboxPageProps) {
  const selectedThread =
    data.threadsById[selectedConversationId] ?? data.threadsById[data.selectedConversationId];
  const resolvedSelectedConversationId =
    selectedThread?.conversationId || selectedConversationId || data.selectedConversationId;

  return (
    <div className="inbox-layout">
      <InboxList
        conversations={data.conversations}
        selectedConversationId={resolvedSelectedConversationId}
        onSelectConversation={onSelectConversation}
      />
      {selectedThread ? (
        <section className="panel-stack">
          <div className="section-heading">
            <h3>Marketing state</h3>
            <span>{selectedThread.bookingStatus || "unclassified"}</span>
          </div>
          <div className="list-card">
            <div className="list-card__row list-card__row--muted">
              <span>Sequence</span>
              <span>{selectedThread.sequenceStatus || "none"}</span>
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>Next step</span>
              <span>{selectedThread.nextSequenceStep || "none"}</span>
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>Manual call due</span>
              <span>{selectedThread.manualCallDueAt || "not scheduled"}</span>
            </div>
            <div className="list-card__row list-card__row--muted">
              <span>Recent reply</span>
              <span>{selectedThread.recentReplyPreview || "none"}</span>
            </div>
          </div>
          <ConversationThread thread={selectedThread} />
        </section>
      ) : (
        <section className="panel-stack">
          <div className="section-heading">
            <h3>Conversation</h3>
            <span>No thread selected</span>
          </div>
        </section>
      )}
    </div>
  );
}
