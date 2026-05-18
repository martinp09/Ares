import { useEffect, useMemo, useState } from "react";

import type { OutboundSendResponse, SelectedThread } from "../lib/api";

interface ConversationThreadProps {
  thread: SelectedThread;
  onSendSmsTest: (payload: { to: string; body: string }) => Promise<OutboundSendResponse>;
  onSendEmailTest: (payload: { to: string; subject: string; text: string; html?: string | null }) => Promise<OutboundSendResponse>;
}

export function ConversationThread({ thread, onSendSmsTest, onSendEmailTest }: ConversationThreadProps) {
  const [smsTo, setSmsTo] = useState(thread.phone ?? "");
  const [smsBody, setSmsBody] = useState("hello human");
  const [emailTo, setEmailTo] = useState(thread.email ?? "");
  const [emailSubject, setEmailSubject] = useState(`Mission Control test for ${thread.leadName}`);
  const [emailText, setEmailText] = useState("hello human");
  const [smsResult, setSmsResult] = useState<OutboundSendResponse | null>(null);
  const [emailResult, setEmailResult] = useState<OutboundSendResponse | null>(null);
  const [isSendingSms, setIsSendingSms] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const smsAgent = thread.smsAgent;

  const hasSmsTarget = useMemo(() => smsTo.trim().length > 0, [smsTo]);
  const hasEmailTarget = useMemo(() => emailTo.trim().length > 0, [emailTo]);

  useEffect(() => {
    setSmsTo(thread.phone ?? "");
    setSmsBody("hello human");
    setEmailTo(thread.email ?? "");
    setEmailSubject(`Mission Control test for ${thread.leadName}`);
    setEmailText("hello human");
    setSmsResult(null);
    setEmailResult(null);
  }, [thread]);

  async function handleSendSms() {
    if (!hasSmsTarget) {
      return;
    }
    setIsSendingSms(true);
    try {
      const result = await onSendSmsTest({ to: smsTo.trim(), body: smsBody.trim() });
      setSmsResult(result);
    } finally {
      setIsSendingSms(false);
    }
  }

  async function handleSendEmail() {
    if (!hasEmailTarget) {
      return;
    }
    setIsSendingEmail(true);
    try {
      const result = await onSendEmailTest({
        to: emailTo.trim(),
        subject: emailSubject.trim(),
        text: emailText.trim(),
      });
      setEmailResult(result);
    } finally {
      setIsSendingEmail(false);
    }
  }

  return (
    <section className="panel-stack">
      <div className="section-heading">
        <div>
          <h3>{thread.leadName}</h3>
          <p>{thread.company}</p>
        </div>
        <span>{thread.stage}</span>
      </div>
      <section className="conversation-context-grid" aria-label="Conversation desk context">
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Owner</p>
          <strong>{smsAgent?.manualControl ? "Martin" : "Appointment Setter"}</strong>
          <p className="list-card__body list-card__body--muted">Instant takeover stays disabled until wired through Ares policy.</p>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Acquisition route</p>
          <strong>{thread.nextBestAction}</strong>
          <p className="list-card__body list-card__body--muted">{thread.replyNeedsReview ? "Needs Martin review" : "Continue qualification"}</p>
        </article>
        <article className="summary-card summary-card--compact">
          <p className="summary-card__label">Tags</p>
          <div className="pill-row">
            {thread.tags.length > 0 ? thread.tags.map((tag) => <span className="status-pill" key={tag}>{tag}</span>) : <span className="status-pill">unlabeled</span>}
          </div>
        </article>
      </section>
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

      {smsAgent ? (
        <section className="panel-stack conversation-desk-panel" aria-label="Appointment Setter decision review">
          <div className="section-heading">
            <div>
              <h3>Appointment Setter</h3>
              <p>Jailed SMS ISA · Ares owns send, calendar, Slack, and policy</p>
            </div>
            <span>{smsAgent.leadBucket ?? smsAgent.action ?? "review"}</span>
          </div>
          <div className="summary-grid summary-grid--secondary">
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Qualification score</p>
              <strong>{smsAgent.qualificationScore ?? 0}/100</strong>
              <p className="list-card__body list-card__body--muted">Stage: {smsAgent.stage ?? "unknown"}</p>
            </article>
            <article className="summary-card summary-card--compact">
              <p className="summary-card__label">Next action</p>
              <strong>{smsAgent.nextBestAction ?? smsAgent.action ?? "review"}</strong>
              <p className="list-card__body list-card__body--muted">
                {smsAgent.appointmentReady ? "Appointment-ready" : smsAgent.nurtureRecommended ? "Nurture candidate" : "Qualify first"}
              </p>
            </article>
          </div>
          <div className="list-card__row list-card__row--muted">
            <span>{smsAgent.intent ?? "unknown intent"}</span>
            <span>{smsAgent.sourceLane ?? "unknown lane"}</span>
            {smsAgent.urgency ? <span>{smsAgent.urgency}</span> : null}
            {smsAgent.manualControl ? <span>manual takeover</span> : null}
          </div>
          {smsAgent.suggestedBody ? <p className="list-card__body">{smsAgent.suggestedBody}</p> : null}
          {smsAgent.policyReason ? (
            <p className="list-card__body list-card__body--muted">{smsAgent.policyReason}</p>
          ) : null}
          {smsAgent.missingFields && smsAgent.missingFields.length > 0 ? (
            <div className="pill-row" aria-label="Missing qualification fields">
              {smsAgent.missingFields.map((field) => (
                <span className="status-pill" key={field}>{field.replaceAll("_", " ")}</span>
              ))}
            </div>
          ) : null}
          {smsAgent.riskFlags && smsAgent.riskFlags.length > 0 ? (
            <div className="pill-row" aria-label="Appointment Setter risk flags">
              {smsAgent.riskFlags.map((flag) => (
                <span className="status-pill status-pill--danger" key={flag}>{flag.replaceAll("_", " ")}</span>
              ))}
            </div>
          ) : null}
          <div className="list-card__row">
            <button className="button--ghost" disabled type="button">
              Take over thread
            </button>
            <button className="button--ghost" disabled type="button">
              Approve reply
            </button>
            <button className="button--ghost" disabled type="button">
              Request slots
            </button>
            <button className="button--ghost" disabled type="button">
              Send to nurture
            </button>
            <button className="button--ghost" disabled type="button">
              Disqualify
            </button>
          </div>
        </section>
      ) : null}

      <section className="panel-stack">
        <div className="section-heading">
          <h3>Live provider test</h3>
          <span>TextGrid / Resend</span>
        </div>

        <div className="summary-grid summary-grid--secondary">
          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">TextGrid SMS</p>
            <div className="list-card__row list-card__row--muted">
              <input
                aria-label="SMS to"
                className="search-field__input"
                placeholder="+13475550123"
                value={smsTo}
                onChange={(event) => setSmsTo(event.target.value)}
              />
            </div>
            <textarea
              aria-label="SMS body"
              className="search-field__input"
              rows={3}
              style={{ marginTop: "0.75rem", resize: "vertical" }}
              value={smsBody}
              onChange={(event) => setSmsBody(event.target.value)}
            />
            <button className="nav-item" disabled={isSendingSms || !hasSmsTarget} onClick={handleSendSms} type="button">
              {isSendingSms ? "Sending..." : "Send SMS test"}
            </button>
            {smsResult ? (
              <p className="list-card__body list-card__body--muted">
                {smsResult.status} · {smsResult.providerMessageId ?? "no provider id"}
                {smsResult.errorMessage ? ` · ${smsResult.errorMessage}` : ""}
              </p>
            ) : null}
          </article>

          <article className="summary-card summary-card--compact">
            <p className="summary-card__label">Resend email</p>
            <div className="list-card__row list-card__row--muted">
              <input
                aria-label="Email to"
                className="search-field__input"
                placeholder="martinhomeoffers@gmail.com"
                value={emailTo}
                onChange={(event) => setEmailTo(event.target.value)}
              />
            </div>
            <input
              aria-label="Email subject"
              className="search-field__input"
              placeholder="Mission Control email test"
              style={{ marginTop: "0.75rem" }}
              value={emailSubject}
              onChange={(event) => setEmailSubject(event.target.value)}
            />
            <textarea
              aria-label="Email body"
              className="search-field__input"
              rows={3}
              style={{ marginTop: "0.75rem", resize: "vertical" }}
              value={emailText}
              onChange={(event) => setEmailText(event.target.value)}
            />
            <button className="nav-item" disabled={isSendingEmail || !hasEmailTarget} onClick={handleSendEmail} type="button">
              {isSendingEmail ? "Sending..." : "Send email test"}
            </button>
            {emailResult ? (
              <p className="list-card__body list-card__body--muted">
                {emailResult.status} · {emailResult.providerMessageId ?? "no provider id"}
                {emailResult.errorMessage ? ` · ${emailResult.errorMessage}` : ""}
              </p>
            ) : null}
          </article>
        </div>
      </section>
    </section>
  );
}
