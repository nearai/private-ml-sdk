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
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(host=host, port=port, db=db, password=password)
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
            value = self.redis_client.get(key)
            return value.decode("utf-8") if value else None
        except (redis.RedisError, UnicodeDecodeError) as e:
            log.error(f"Redis get error: {e}")
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

    def get_all_keys(self, prefix: str) -> Optional[list]:
        """
        Get all keys with a given prefix
        """
        try:
            return self.redis_client.keys(f"{prefix}:*")
        except redis.RedisError:
            return None

    def get_all_values(self, prefix: str) -> Optional[list]:
        """
        Get all values with a given prefix
        """
        keys = self.get_all_keys(prefix)
        return [self.get_string(key) for key in keys]
