import { invokeRuntimeApi, type RuntimeApiInvokeOptions } from "../shared/runtimeApi";

import { LEAD_MACHINE_ENDPOINTS } from "./runtime";

export type LeadMachineEndpointKey = keyof typeof LEAD_MACHINE_ENDPOINTS;

export async function invokeLeadMachineRuntimeApi<TResponse, TPayload = unknown>(
  endpoint: LeadMachineEndpointKey,
  payload: TPayload,
  options: RuntimeApiInvokeOptions = {}
): Promise<TResponse> {
  return await invokeRuntimeApi<TResponse, TPayload>(LEAD_MACHINE_ENDPOINTS[endpoint], payload, options);
}
