import { task } from "@trigger.dev/sdk";

import { invokeRuntimeApi } from "../shared/runtimeApi";
import { LEAD_MACHINE_ENDPOINTS, type TaskReminderOrOverduePayload, type TaskReminderOrOverdueResponse } from "./runtime";

export const taskReminderOrOverdue = task({
  id: "task-reminder-or-overdue",
  run: async (payload: TaskReminderOrOverduePayload) => {
    return await invokeRuntimeApi<TaskReminderOrOverdueResponse, TaskReminderOrOverduePayload>(
      LEAD_MACHINE_ENDPOINTS.taskReminderOrOverdue,
      payload
    );
  },
});
