import { render, screen, within } from "@testing-library/react";

import { TasksPage } from "./TasksPage";
import type { TasksData } from "../lib/api";

const tasksFixture: TasksData = {
  dueCount: 2,
  tasks: [
    {
      threadId: "mc_thread_1",
      leadName: "Jordan Pending",
      channel: "sms",
      bookingStatus: "pending",
      sequenceStatus: "active",
      nextSequenceStep: "manual_call_day_3",
      manualCallDueAt: "2026-04-14T18:45:00+00:00",
      recentReplyPreview: "If this works I can jump on a call tonight.",
      replyNeedsReview: true,
    },
    {
      threadId: "mc_thread_2",
      leadName: "Morgan Callback",
      channel: "call",
      bookingStatus: "pending",
      sequenceStatus: "paused",
      nextSequenceStep: "manual_call_followup",
      manualCallDueAt: "2026-04-14T19:15:00+00:00",
      recentReplyPreview: null,
      replyNeedsReview: false,
    },
    {
      threadId: "task_provider_1",
      leadName: "+15551230003",
      channel: "confirmation_sms",
      bookingStatus: "pending",
      sequenceStatus: "active",
      nextSequenceStep: "confirmation_sms",
      manualCallDueAt: "2026-04-14T19:30:00+00:00",
      recentReplyPreview: null,
      replyNeedsReview: true,
      priority: "high",
      providerFailure: true,
      errorMessage: "textgrid down",
    },
  ],
};

describe("TasksPage", () => {
  it("renders due manual-call tasks with marketing state", () => {
    render(<TasksPage data={tasksFixture} />);

    expect(screen.getByText("Manual call queue")).toBeInTheDocument();
    expect(screen.getByText("2 due")).toBeInTheDocument();

    const firstTask = screen.getByLabelText("manual-call-mc_thread_1");
    expect(within(firstTask).getByText("Jordan Pending")).toBeInTheDocument();
    expect(within(firstTask).getByText("pending")).toBeInTheDocument();
    expect(within(firstTask).getByText("active")).toBeInTheDocument();
    expect(within(firstTask).getByText("Review required")).toBeInTheDocument();
    expect(
      within(firstTask).getByText("If this works I can jump on a call tonight."),
    ).toBeInTheDocument();

    const providerFailureTask = screen.getByLabelText("manual-call-task_provider_1");
    expect(within(providerFailureTask).getByText("provider failure")).toBeInTheDocument();
    expect(within(providerFailureTask).getByText("high")).toBeInTheDocument();
    expect(within(providerFailureTask).getByText("textgrid down")).toBeInTheDocument();
  });

  it("renders an empty state when no manual calls are due", () => {
    render(<TasksPage data={{ dueCount: 0, tasks: [] }} />);

    expect(screen.getByText("No manual calls due")).toBeInTheDocument();
  });
});
