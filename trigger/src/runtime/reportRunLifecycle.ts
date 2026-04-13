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

  return invokeRuntimeApi<TResponse, Record<string, unknown>>(
    `/trigger/callbacks/runs/${payload.runId}/${suffix}`,
    payload
  );
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
