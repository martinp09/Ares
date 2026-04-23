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
  const resolvedConversationId = selectedThread?.conversationId ?? "";

  return (
    <div className="inbox-layout">
      <InboxList
        conversations={data.conversations}
        selectedConversationId={resolvedConversationId}
        onSelectConversation={onSelectConversation}
      />
      {selectedThread ? (
        <ConversationThread
          thread={selectedThread}
          onSendSmsTest={onSendSmsTest}
          onSendEmailTest={onSendEmailTest}
        />
      ) : (
        <section className="panel-stack" aria-label="inbox-thread-placeholder">
          <div className="section-heading">
            <h3>Conversation detail</h3>
            <span>Waiting for thread</span>
          </div>
          <div className="list-card">
            <p className="list-card__body">Select a thread to inspect context.</p>
          </div>
        </section>
      )}
    </div>
  );
}
