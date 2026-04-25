import { defineConfig } from "@trigger.dev/sdk";

const triggerProjectRef = process.env.TRIGGER_PROJECT_REF ?? "proj_puouljyhwiraonjkpiki";

export default defineConfig({
  project: triggerProjectRef,
  dirs: ["./src"],
  maxDuration: 300,
  retries: {
    enabledInDev: false,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 10000,
      factor: 2,
      randomize: true
    }
  }
});
