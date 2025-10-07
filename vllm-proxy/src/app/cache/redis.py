import os
from typing import Optional

import redis
from app.logger import log

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))


class RedisCache:
    """Redis cache implementation that reads connection details from environment variables"""

    def __init__(
        self,
        expiration: int,
        host: str = REDIS_HOST,
        port: int = REDIS_PORT,
        password: str = REDIS_PASSWORD,
        db: int = REDIS_DB,
    ):
        """Initialize Redis connection (lazy - allows hot-adding Redis later)"""
        self.redis_client = redis.Redis(
            host=host, port=port, db=db, password=password,
            socket_connect_timeout=2, socket_timeout=2, decode_responses=True
        )
        self.expiration = expiration

    def set_string(self, key: str, value: str) -> bool:
        """
        Store chat data in Redis
        Args:
            key: unique identifier for the key
            value: string value to store
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.redis_client.set(key, value, ex=self.expiration)
            return True
        except redis.RedisError:
            return False

    def get_string(self, key: str) -> Optional[str]:
        """
        Retrieve chat data from Redis
        Args:
            key: unique identifier for the key
        Returns:
            str: cached value if exists, None otherwise
        """
        try:
            # decode_responses=True handles decoding automatically
            return self.redis_client.get(key)
        except redis.RedisError as e:
            log.error("Redis get error: %s", e)
            return None

    def delete(self, key: str) -> bool:
        """
        Delete data from Redis
        Args:
            key: unique identifier for the key
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError:
            return False

    def get_all_values(self, prefix: str) -> list[str]:
        """
        Get all values with a given prefix using SCAN (non-blocking)
        """
        try:
            values = []
            pattern = f"{prefix}:*"
            # Use SCAN instead of KEYS to avoid blocking Redis
            for key in self.redis_client.scan_iter(match=pattern, count=100):
                value = self.redis_client.get(key)
                if value:
                    values.append(value)
            return values
        except redis.RedisError as e:
            log.error("Redis scan error: %s", e)
            return []
