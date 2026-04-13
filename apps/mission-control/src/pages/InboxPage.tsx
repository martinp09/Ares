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

  return (
    <div className="inbox-layout">
      <InboxList
        conversations={data.conversations}
        selectedConversationId={selectedThread.conversationId}
        onSelectConversation={onSelectConversation}
      />
      <ConversationThread thread={selectedThread} />
    </div>
  );
}
