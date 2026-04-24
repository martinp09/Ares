import { invokeRuntimeApi } from "../shared/runtimeApi";

export type RunLifecycleEventName = "run_started" | "run_completed" | "run_failed" | "artifact_produced";

export type RunLifecycleBasePayload = {
  runId: string;
  commandId: string;
  businessId: string;
  environment: string;
  idempotencyKey: string;
  trigger_run_id?: string;
};

type RunMappedPayload = {
  runId?: string;
  run_id?: string;
  commandId?: string;
  command_id?: string;
  businessId?: string;
  business_id?: string;
  environment?: string;
  idempotencyKey?: string;
  idempotency_key?: string;
  triggerRunId?: string;
  trigger_run_id?: string;
};

function compactPayload(payload: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== undefined));
}

function lifecyclePayloadFrom(payload: RunMappedPayload): RunLifecycleBasePayload {
  const runId = payload.runId ?? payload.run_id;
  const commandId = payload.commandId ?? payload.command_id;
  const businessId = payload.businessId ?? payload.business_id;
  const environment = payload.environment;
  const idempotencyKey = payload.idempotencyKey ?? payload.idempotency_key;

  if (!runId || !commandId || !businessId || !environment || !idempotencyKey) {
    throw new Error(
      "Missing run lifecycle fields: runId, commandId, businessId, environment, and idempotencyKey are required."
    );
  }

  return {
    runId,
    commandId,
    businessId,
    environment,
    idempotencyKey,
    trigger_run_id: payload.trigger_run_id ?? payload.triggerRunId,
  };
}

function hasLifecyclePayload(payload: RunMappedPayload): boolean {
  return Boolean(
    (payload.runId ?? payload.run_id) &&
    (payload.commandId ?? payload.command_id) &&
    (payload.businessId ?? payload.business_id) &&
    payload.environment &&
    (payload.idempotencyKey ?? payload.idempotency_key)
  );
}

export async function reportRunLifecycle<TResponse = unknown>(
  eventName: RunLifecycleEventName,
  payload: Record<string, unknown> & { runId: string }
): Promise<TResponse> {
  const suffix = eventName === "run_started"
    ? "started"
    : eventName === "run_completed"
      ? "completed"
      : eventName === "run_failed"
        ? "failed"
        : "artifacts";

  const body = compactPayload({
    trigger_run_id: payload.trigger_run_id ?? payload.triggerRunId,
    command_id: payload.command_id ?? payload.commandId,
    business_id: payload.business_id ?? payload.businessId,
    environment: payload.environment,
    idempotency_key: payload.idempotency_key ?? payload.idempotencyKey,
    started_at: payload.started_at ?? payload.startedAt,
    completed_at: payload.completed_at ?? payload.completedAt,
    error_classification: payload.error_classification,
    error_message: payload.error_message,
    artifact_type: payload.artifact_type ?? payload.artifactType,
    payload: payload.payload,
  });

  return invokeRuntimeApi<TResponse, Record<string, unknown>>(`/trigger/callbacks/runs/${payload.runId}/${suffix}`, body);
}

export async function reportRunStarted<TResponse = unknown>(
  payload: RunLifecycleBasePayload
): Promise<TResponse> {
  return reportRunLifecycle<TResponse>("run_started", payload);
}

export async function reportRunCompleted<TResponse = unknown>(
  payload: RunLifecycleBasePayload
): Promise<TResponse> {
  return reportRunLifecycle<TResponse>("run_completed", payload);
}

export async function reportRunFailed<TResponse = unknown>(
  payload: RunLifecycleBasePayload & { error_classification: string; error_message: string }
): Promise<TResponse> {
  return reportRunLifecycle<TResponse>("run_failed", payload);
}

export async function reportArtifactProduced<TResponse = unknown>(
  payload: RunLifecycleBasePayload & { artifactType: string; payload: Record<string, unknown> }
): Promise<TResponse> {
  const { artifactType, ...rest } = payload;
  return reportRunLifecycle<TResponse>("artifact_produced", {
    ...rest,
    artifact_type: artifactType,
  });
}

export async function runWithLifecycle<TPayload extends RunMappedPayload, TResponse>(
  payload: TPayload,
  run: () => Promise<TResponse>,
  options: { artifactType?: string } = {}
): Promise<TResponse> {
  const lifecyclePayload = lifecyclePayloadFrom(payload);

  try {
    await reportRunStarted(lifecyclePayload);
    const result = await run();
    if (options.artifactType) {
      await reportArtifactProduced({
        ...lifecyclePayload,
        artifactType: options.artifactType,
        payload: result as Record<string, unknown>,
      });
    }
    await reportRunCompleted(lifecyclePayload);
    return result;
  } catch (error) {
    await reportRunFailed({
      ...lifecyclePayload,
      error_classification: error instanceof Error ? error.name : "unknown_error",
      error_message: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

export async function runWithOptionalLifecycle<TPayload extends RunMappedPayload, TResponse>(
  payload: TPayload,
  run: () => Promise<TResponse>,
  options: { artifactType?: string } = {}
): Promise<TResponse> {
  if (!hasLifecyclePayload(payload)) {
    return await run();
  }

  return await runWithLifecycle(payload, run, options);
}
