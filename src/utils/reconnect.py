"""
Reconnection delay manager with thread-safe state tracking.
"""

import threading


class ReconnectDelay:
    """
    Tracks and provides the next reconnection delay.

    Currently uses a fixed 10-second delay; designed for future
    exponential-backoff logic.
    """

    def __init__(self) -> None:
        self._delay: int | None = None
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear the stored delay, allowing the next call to start fresh."""
        with self._lock:
            self._delay = None

    def get_next(self) -> int:
        """
        Return the next delay in seconds.

        Returns:
            Delay value in seconds (currently always 10).
        """
        with self._lock:
            self._delay = 10
            return self._delay
