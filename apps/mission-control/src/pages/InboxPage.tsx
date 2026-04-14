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
        <ConversationThread thread={selectedThread} />
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
