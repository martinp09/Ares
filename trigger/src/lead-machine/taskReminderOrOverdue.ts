import { task } from "@trigger.dev/sdk";

import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type TaskReminderOrOverduePayload, type TaskReminderOrOverdueResponse } from "./runtime";

export const taskReminderOrOverdue = task({
  id: "task-reminder-or-overdue",
  run: async (payload: TaskReminderOrOverduePayload) => {
    return await invokeLeadMachineRuntimeApi<TaskReminderOrOverdueResponse, TaskReminderOrOverduePayload>(
      "taskReminderOrOverdue",
      payload
    );
  },
});
