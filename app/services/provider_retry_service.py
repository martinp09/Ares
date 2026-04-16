from __future__ import annotations

import time
from typing import Callable

from app.core.config import Settings, get_settings
from app.models.providers import ProviderRetryState, ProviderTransportError

_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class ProviderRetryService:
    def __init__(self, settings: Settings | None = None, sleep_fn: Callable[[float], None] | None = None) -> None:
        self.settings = settings or get_settings()
        self.sleep_fn = sleep_fn or time.sleep

    def evaluate(self, attempt_number: int, exc: Exception) -> ProviderRetryState:
        retryable = self.is_retryable(exc)
        exhausted = not retryable or attempt_number >= max(1, self.settings.provider_request_max_retries + 1)
        next_delay_seconds = None
        if retryable and not exhausted:
            retry_index = max(0, attempt_number - 1)
            next_delay_seconds = min(
                self.settings.provider_retry_base_delay_seconds * (2 ** retry_index),
                self.settings.provider_retry_max_delay_seconds,
            )
        return ProviderRetryState(
            attempt_count=attempt_number,
            max_attempts=max(1, self.settings.provider_request_max_retries + 1),
            retry_count=max(0, attempt_number - 1),
            retryable=retryable,
            exhausted=exhausted,
            next_delay_seconds=next_delay_seconds,
            last_error=str(exc),
        )

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self.sleep_fn(seconds)

    def is_retryable(self, exc: Exception) -> bool:
        if isinstance(exc, ProviderTransportError):
            if exc.status_code is None:
                return True
            return exc.status_code in _RETRYABLE_STATUS_CODES
        return isinstance(exc, (TimeoutError, ConnectionError, OSError))
