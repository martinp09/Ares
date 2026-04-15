export type RuntimeApiInvokeOptions = {
  apiKey?: string;
};

function getRuntimeApiBaseUrl(): string {
  const rawBaseUrl =
    process.env.HERMES_RUNTIME_API_BASE_URL ?? process.env.RUNTIME_API_BASE_URL;

  if (!rawBaseUrl) {
    throw new Error(
      "Missing HERMES_RUNTIME_API_BASE_URL (or RUNTIME_API_BASE_URL) environment variable."
    );
  }

  return rawBaseUrl.endsWith("/") ? rawBaseUrl.slice(0, -1) : rawBaseUrl;
}

function getRuntimeApiKey(explicitApiKey?: string): string | undefined {
  return explicitApiKey ?? process.env.HERMES_RUNTIME_API_KEY ?? process.env.RUNTIME_API_KEY;
}

export async function invokeRuntimeApi<TResponse, TPayload = unknown>(
  endpointPath: string,
  payload: TPayload,
  options: RuntimeApiInvokeOptions = {}
): Promise<TResponse> {
  const baseUrl = getRuntimeApiBaseUrl();
  const apiKey = getRuntimeApiKey(options.apiKey);
  const normalizedPath = endpointPath.startsWith("/") ? endpointPath : `/${endpointPath}`;

  const headers: Record<string, string> = {
    "content-type": "application/json"
  };

  if (apiKey) {
    headers.authorization = `Bearer ${apiKey}`;
  }

  const response = await fetch(`${baseUrl}${normalizedPath}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload ?? {})
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `Runtime API request failed (${response.status} ${response.statusText}): ${errorBody}`
    );
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

export async function invokeRuntimeApiWithoutResponse<TPayload = unknown>(
  endpointPath: string,
  payload: TPayload,
  options: RuntimeApiInvokeOptions = {}
): Promise<void> {
  await invokeRuntimeApi<void, TPayload>(endpointPath, payload, options);
}
