import { ConversationThread } from "../components/ConversationThread";
import { InboxList } from "../components/InboxList";
import type { OutboundSendResponse, InboxData } from "../lib/api";

interface InboxPageProps {
  data: InboxData;
  selectedConversationId: string;
  onSelectConversation: (conversationId: string) => void;
  onSendSmsTest: (payload: { to: string; body: string }) => Promise<OutboundSendResponse>;
  onSendEmailTest: (payload: { to: string; subject: string; text: string; html?: string | null }) => Promise<OutboundSendResponse>;
}

export function InboxPage({
  data,
  selectedConversationId,
  onSelectConversation,
  onSendSmsTest,
  onSendEmailTest,
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
      <ConversationThread thread={selectedThread} onSendSmsTest={onSendSmsTest} onSendEmailTest={onSendEmailTest} />
    </div>
  );
}
