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
  const unreadCount = data.conversations.reduce((count, conversation) => count + conversation.unreadCount, 0);
  const selectedConversation = data.conversations.find((conversation) => conversation.id === resolvedConversationId);

  return (
    <div className="inbox-layout inbox-layout--crm">
      <aside className="inbox-scope-panel" aria-label="Inbox scopes">
        <div className="section-heading">
          <h3>Inbox scopes</h3>
          <span>{data.conversations.length} threads</span>
        </div>
        <div className="inbox-scope-list">
          <button type="button" className="inbox-scope inbox-scope--active">
            <span>My Inbox</span>
            <strong>{unreadCount}</strong>
          </button>
          <button type="button" className="inbox-scope">
            <span>Team Inbox</span>
            <strong>{data.conversations.length}</strong>
          </button>
          <button type="button" className="inbox-scope">
            <span>Internal</span>
            <strong>{selectedThread?.notes.length ?? 0}</strong>
          </button>
          <button type="button" className="inbox-scope">
            <span>Unread</span>
            <strong>{unreadCount}</strong>
          </button>
        </div>
      </aside>

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
      <aside className="conversation-context" aria-label="Conversation context">
        <div className="section-heading">
          <h3>CRM context</h3>
          <span>{selectedConversation?.stage ?? selectedThread?.stage ?? "No thread"}</span>
        </div>
        <div className="context-card">
          <strong>Linked opportunity</strong>
          <span>{selectedThread ? `${selectedThread.stage} | ${selectedThread.nextBestAction}` : "Select a thread to inspect context."}</span>
        </div>
        <div className="context-card">
          <strong>Owner</strong>
          <span>{selectedThread?.leadName ?? "No owner selected"}</span>
        </div>
        <div className="context-card">
          <strong>Contact channels</strong>
          <span>{selectedThread?.phone ?? selectedThread?.email ?? "No channel on selected thread"}</span>
        </div>
        <div className="context-card">
          <strong>Tags</strong>
          <span>{selectedThread?.tags.join(", ") || "No tags"}</span>
        </div>
        <div className="context-card">
          <strong>Agent actions</strong>
          <div className="agent-action-grid">
            <button type="button">Draft reply</button>
            <button type="button">Suggest stage move</button>
            <button type="button">Create task</button>
          </div>
        </div>
      </aside>
    </div>
  );
}
