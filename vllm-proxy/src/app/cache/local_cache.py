from typing import Optional

from cachetools import TTLCache


class LocalCache:
    """Class for local cache implementations"""

    def __init__(self, expiration: int):
        self.cache = TTLCache(maxsize=1000, ttl=expiration)

    def set(self, key: str, value: str):
        """Set a value in the cache"""
        self.cache[key] = value

    def get(self, key: str) -> Optional[str]:
        """Get a value from the cache"""
        return self.cache.get(key)
