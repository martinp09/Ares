import { task } from "@trigger.dev/sdk";

export const bootstrapTask = task({
  id: "bootstrap-task",
  run: async (payload: { message?: string } = {}) => {
    return {
      ok: true,
      message: payload.message ?? "Hermes Central Command Trigger.dev bootstrap is running"
    };
  }
});
