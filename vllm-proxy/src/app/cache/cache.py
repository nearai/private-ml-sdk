import json
import os
from typing import Optional

from app.logger import log

from .local_cache import LocalCache
from .redis import RedisCache

CHAT_CACHE_EXPIRATION = int(
    os.getenv("CHAT_CACHE_EXPIRATION", "1200")
)  # 20 minutes by default

CHAT_PREFIX = "chat"
ATTESTATION_PREFIX = "attestation"


class ChatCache:
    """Class for chat cache implementations"""

    def __init__(self):
        self.redis_cache = RedisCache(expiration=CHAT_CACHE_EXPIRATION)
        self.local_cache = LocalCache(expiration=CHAT_CACHE_EXPIRATION)

    def _get_key(self, prefix: str, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{prefix}:{key}"

    def set_chat(self, chat_id: str, chat: str) -> bool:
        """Set chat history by chat_id
        If Redis is not available, use local cache
        """
        try:
            key = self._get_key(CHAT_PREFIX, chat_id)
            if not self.redis_cache.set_string(key, chat):
                log.warning(
                    f"Failed to set chat {chat_id} in Redis, falling back to local cache"
                )
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
            key = self._get_key(CHAT_PREFIX, chat_id)
            value = self.redis_cache.get_string(key)
            if not value:
                value = self.local_cache.get(key)
            return value
        except Exception as e:
            log.error(f"Error getting chat from cache: {e}")
            return None

    def set_attestation(self, ecdsa_address: str, attestation: object) -> bool:
        """Set attestation by ecdsa_address"""
        try:
            value = json.dumps(attestation)
            key = self._get_key(ATTESTATION_PREFIX, ecdsa_address)
            if not self.redis_cache.set_string(key, value):
                log.warning(f"Failed to set attestation for {ecdsa_address} in Redis")
                self.local_cache.set(key, value)
        except Exception as e:
            log.error(f"Error setting attestation in cache: {e}")
            return False
        return True

    def get_attestations(self) -> list:
        """Get all attestations"""
        try:
            values = self.redis_cache.get_all_values(ATTESTATION_PREFIX)
            return [json.loads(value) for value in values]
        except Exception as e:
            log.error(f"Error getting attestation from cache: {e}")
            return []


cache = ChatCache()
