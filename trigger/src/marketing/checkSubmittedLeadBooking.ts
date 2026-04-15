import { task, tasks } from "@trigger.dev/sdk";
import { leadSequenceQueueKey } from "../runtime/queueKeys";
import { invokeRuntimeApi } from "../shared/runtimeApi";

export type CheckSubmittedLeadBookingPayload = {
  leadId: string;
  businessId: string;
  environment: string;
};

type NonBookerCheckResponse = {
  bookingStatus: "pending" | "booked" | "cancelled" | "rescheduled";
  shouldEnrollInSequence: boolean;
  startDay?: number;
};

export const checkSubmittedLeadBooking = task({
  id: "marketing-check-submitted-lead-booking",
  run: async (payload: CheckSubmittedLeadBookingPayload) => {
    const result = await invokeRuntimeApi<NonBookerCheckResponse, CheckSubmittedLeadBookingPayload>(
      "/marketing/internal/non-booker-check",
      payload
    );

    if (result.bookingStatus !== "pending" || !result.shouldEnrollInSequence) {
      return {
        leadId: payload.leadId,
        enrolled: false,
        reason: "already_booked_or_not_eligible",
      };
    }

    await tasks.trigger("marketing-run-lease-option-sequence-step", {
      ...payload,
      day: result.startDay ?? 0,
    }, {
      queue: leadSequenceQueueKey(payload.businessId, payload.environment, payload.leadId),
    });

    return {
      leadId: payload.leadId,
      enrolled: true,
      startDay: result.startDay ?? 0,
    };
  },
});
