import { task, tasks } from "@trigger.dev/sdk";
import { leadSequenceQueueKey } from "../runtime/queueKeys";
import { runWithOptionalLifecycle } from "../runtime/reportRunLifecycle";
import { invokeRuntimeApi } from "../shared/runtimeApi";

type LeaseOptionSequenceStep = {
  day: number;
  channel: "sms" | "email";
  templateId: string;
  manualCallCheckpoint?: boolean;
};

const LEASE_OPTION_SEQUENCE_STEPS: LeaseOptionSequenceStep[] = [
  { day: 0, channel: "sms", templateId: "lease_option_day_0_sms" },
  { day: 1, channel: "sms", templateId: "lease_option_day_1_sms" },
  { day: 2, channel: "sms", templateId: "lease_option_day_2_sms", manualCallCheckpoint: true },
  { day: 4, channel: "sms", templateId: "lease_option_day_4_sms" },
  { day: 6, channel: "sms", templateId: "lease_option_day_6_sms", manualCallCheckpoint: true },
  { day: 8, channel: "email", templateId: "lease_option_day_8_email" },
  { day: 10, channel: "sms", templateId: "lease_option_day_10_sms", manualCallCheckpoint: true },
];

export type RunLeaseOptionSequenceStepPayload = {
  leadId: string;
  businessId: string;
  environment: string;
  day: number;
  runId?: string;
  commandId?: string;
  idempotencyKey?: string;
  triggerRunId?: string;
};

type SequenceGuardResponse = {
  bookingStatus: "pending" | "booked" | "cancelled" | "rescheduled";
  sequenceStatus: "active" | "paused" | "completed" | "stopped";
  optedOut: boolean;
};

type SequenceDispatchResponse = {
  messageId: string;
  channel: "sms" | "email";
  status: "queued" | "sent" | "skipped";
};

function findNextStep(day: number): LeaseOptionSequenceStep | undefined {
  return LEASE_OPTION_SEQUENCE_STEPS.find((step) => step.day > day);
}

export const runLeaseOptionSequenceStep = task({
  id: "marketing-run-lease-option-sequence-step",
  run: async (payload: RunLeaseOptionSequenceStepPayload) => {
    return await runWithOptionalLifecycle(payload, async () => {
      const currentStep = LEASE_OPTION_SEQUENCE_STEPS.find((step) => step.day === payload.day);
      if (!currentStep) {
        return {
          leadId: payload.leadId,
          day: payload.day,
          status: "skipped_unknown_step",
        };
      }

      const guard = await invokeRuntimeApi<SequenceGuardResponse, RunLeaseOptionSequenceStepPayload>(
        "/marketing/internal/lease-option-sequence/guard",
        payload
      );

      if (
        guard.bookingStatus !== "pending" ||
        guard.sequenceStatus !== "active" ||
        guard.optedOut
      ) {
        return {
          leadId: payload.leadId,
          day: payload.day,
          status: "stopped",
        };
      }

      const dispatch = await invokeRuntimeApi<
        SequenceDispatchResponse,
        RunLeaseOptionSequenceStepPayload & LeaseOptionSequenceStep
      >("/marketing/internal/lease-option-sequence/step", {
        ...payload,
        ...currentStep,
      });

      if (currentStep.manualCallCheckpoint) {
        await tasks.trigger("marketing-create-manual-call-task", {
          leadId: payload.leadId,
          businessId: payload.businessId,
          environment: payload.environment,
          sequenceDay: currentStep.day,
          reason: "lease_option_sequence_checkpoint",
        }, {
          queue: leadSequenceQueueKey(payload.businessId, payload.environment, payload.leadId),
        });
      }

      const nextStep = findNextStep(currentStep.day);
      if (nextStep) {
        await tasks.trigger("marketing-run-lease-option-sequence-step", {
          leadId: payload.leadId,
          businessId: payload.businessId,
          environment: payload.environment,
          day: nextStep.day,
        }, {
          queue: leadSequenceQueueKey(payload.businessId, payload.environment, payload.leadId),
          delay: `${nextStep.day - currentStep.day}d`,
        });
      }

      return {
        leadId: payload.leadId,
        day: currentStep.day,
        messageId: dispatch.messageId,
        channel: dispatch.channel,
        status: dispatch.status,
        nextDay: nextStep?.day,
      };
    });
  },
});
