import { task } from "@trigger.dev/sdk";
import { leadSequenceQueueKey } from "../runtime/queueKeys";
import { runWithOptionalLifecycle } from "../runtime/reportRunLifecycle";
import { invokeRuntimeApi } from "../shared/runtimeApi";

export type SendAppointmentReminderPayload = {
  leadId: string;
  businessId: string;
  environment: string;
  reminderLabel: "24h" | "1h" | string;
  startsAt?: string | null;
  bookingId?: string | null;
  runId?: string;
  commandId?: string;
  idempotencyKey?: string;
  triggerRunId?: string;
};

type AppointmentReminderResponse = {
  leadId: string;
  status: "queued" | "skipped" | "failed" | string;
  smsProviderMessageId?: string | null;
  emailProviderMessageId?: string | null;
};

export const sendAppointmentReminder = task({
  id: "marketing-send-appointment-reminder",
  queue: {
    concurrencyLimit: 1,
  },
  run: async (payload: SendAppointmentReminderPayload) => {
    return await runWithOptionalLifecycle(payload, async () => {
      const result = await invokeRuntimeApi<AppointmentReminderResponse, SendAppointmentReminderPayload>(
        "/marketing/internal/appointment-reminder",
        payload
      );

      return {
        leadId: result.leadId,
        bookingId: payload.bookingId ?? null,
        reminderLabel: payload.reminderLabel,
        startsAt: payload.startsAt ?? null,
        status: result.status,
        smsProviderMessageId: result.smsProviderMessageId ?? null,
        emailProviderMessageId: result.emailProviderMessageId ?? null,
        queue: leadSequenceQueueKey(payload.businessId, payload.environment, payload.leadId),
      };
    });
  },
});
