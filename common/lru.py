"""
Simple LRU (Least Recently Used) cache backed by OrderedDict.
"""

from collections import OrderedDict
from typing import TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(OrderedDict[K, V]):
    """Dict-like LRU cache that discards the oldest item when full."""

    def __init__(self, maxsize: int = 10000) -> None:
        """
        Args:
            maxsize: Maximum number of items before eviction.
        """
        super().__init__()
        self._maxsize = maxsize

    def __getitem__(self, key: K) -> V:
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        while len(self) >= self._maxsize:
            self.popitem(last=False)
        super().__setitem__(key, value)
