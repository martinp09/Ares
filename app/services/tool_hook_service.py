from __future__ import annotations

from collections.abc import Callable

from app.models.tool_hooks import ToolHookContext, ToolHookPhase

ToolHook = Callable[[ToolHookContext], None]


class ToolHookService:
    def __init__(
        self,
        before_hooks: list[ToolHook] | None = None,
        after_hooks: list[ToolHook] | None = None,
    ) -> None:
        self.before_hooks = list(before_hooks or [])
        self.after_hooks = list(after_hooks or [])

    def register_before_hook(self, hook: ToolHook) -> None:
        self.before_hooks.append(hook)

    def register_after_hook(self, hook: ToolHook) -> None:
        self.after_hooks.append(hook)

    def before_tool_call(self, context: ToolHookContext) -> None:
        self._notify(self.before_hooks, context.model_copy(update={"phase": ToolHookPhase.BEFORE_TOOL_CALL}))

    def after_tool_call(self, context: ToolHookContext) -> None:
        self._notify(self.after_hooks, context.model_copy(update={"phase": ToolHookPhase.AFTER_TOOL_CALL}))

    def _notify(self, hooks: list[ToolHook], context: ToolHookContext) -> None:
        for hook in hooks:
            hook(context)


tool_hook_service = ToolHookService()
