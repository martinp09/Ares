import { defineConfig, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";

const runtimeEnv = globalThis as typeof globalThis & {
  process?: { env?: Record<string, string | undefined> };
};
const env = runtimeEnv.process?.env ?? {};
const runtimeApiBaseUrl =
  env.RUNTIME_API_BASE_URL ?? env.HERMES_RUNTIME_API_BASE_URL ?? "http://127.0.0.1:8000";
const runtimeApiKey = env.RUNTIME_API_KEY ?? env.HERMES_RUNTIME_API_KEY;

function runtimeProxy(runtimeApiBaseUrl: string, runtimeApiKey?: string): ProxyOptions {
  return {
    target: runtimeApiBaseUrl,
    changeOrigin: true,
    configure(proxy) {
      proxy.on("proxyReq", (proxyReq) => {
        if (runtimeApiKey) {
          proxyReq.setHeader("Authorization", `Bearer ${runtimeApiKey}`);
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/agent-assets": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/agent-installs": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/agents": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/approvals": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/catalog": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/commands": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/health": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/hermes": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/memberships": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/mission-control": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/organizations": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/outcomes": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/permissions": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/release-management": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/replays": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/runs": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/sessions": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/site-events": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/skills": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
      "/usage": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey),
    },
  },
});
