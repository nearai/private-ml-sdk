import os
from typing import Optional

from .local_cache import LocalCache
from .redis import RedisCache
from app.logger import log

CHAT_CACHE_EXPIRATION = int(
    os.getenv("CHAT_CACHE_EXPIRATION", "1200")
)  # 20 minutes by default


class ChatCache:
    """Class for chat cache implementations"""

    def __init__(self):
        self.redis_cache = RedisCache(expiration=CHAT_CACHE_EXPIRATION)
        self.local_cache = LocalCache(expiration=CHAT_CACHE_EXPIRATION)
        self.prefix = "chat:"

    def _get_key(self, chat_id: str) -> str:
        """Generate cache key with prefix"""
        return f"{self.prefix}{chat_id}"

    def set_chat(self, chat_id: str, chat: str) -> bool:
        """Set chat history by chat_id
        If Redis is not available, use local cache
        """
        try:
            key = self._get_key(chat_id)
            if not self.redis_cache.set_string(key, chat):
                log.warning(f"Failed to set chat {chat_id} in Redis, falling back to local cache")
                self.local_cache.set(key, chat)
        except Exception as e:
            log.error(f"Error setting chat in cache: {e}")
            return False
        return True

    def get_chat(self, chat_id: str) -> Optional[str]:
        """Get chat history by chat_id
        If Redis is not available, use local cache
        """
        try:
            key = self._get_key(chat_id)
            value = self.redis_cache.get_string(key)
            if not value:
                value = self.local_cache.get(key)
            return value
        except Exception as e:
            log.error(f"Error getting chat from cache: {e}")
            return None

cache = ChatCache()