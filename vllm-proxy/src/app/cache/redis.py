import os
import time
from typing import Optional

import redis
from app.logger import log

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Circuit breaker: skip Redis for this duration after failure
CIRCUIT_BREAKER_DURATION = 10  # seconds


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
            socket_connect_timeout=0.1,  # 100ms - fail fast
            socket_timeout=0.1,  # 100ms - fail fast
            decode_responses=True
        )
        self.expiration = expiration
        self._circuit_breaker_until = 0.0  # timestamp to skip Redis until

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is active (Redis is being skipped)."""
        return time.time() < self._circuit_breaker_until

    def _open_circuit(self) -> None:
        """Open circuit breaker - skip Redis for configured duration."""
        self._circuit_breaker_until = time.time() + CIRCUIT_BREAKER_DURATION
        log.warning("Redis circuit breaker opened for %ds", CIRCUIT_BREAKER_DURATION)

    def set_string(self, key: str, value: str) -> bool:
        """
        Store chat data in Redis
        Args:
            key: unique identifier for the key
            value: string value to store
        Returns:
            bool: True if successful, False otherwise
        """
        if self._is_circuit_open():
            return False

        try:
            self.redis_client.set(key, value, ex=self.expiration)
            return True
        except redis.RedisError:
            self._open_circuit()
            return False

    def get_string(self, key: str) -> Optional[str]:
        """
        Retrieve chat data from Redis
        Args:
            key: unique identifier for the key
        Returns:
            str: cached value if exists, None otherwise
        """
        if self._is_circuit_open():
            return None

        try:
            # decode_responses=True handles decoding automatically
            return self.redis_client.get(key)
        except redis.RedisError as e:
            log.error("Redis get error: %s", e)
            self._open_circuit()
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
        if self._is_circuit_open():
            return []

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
            self._open_circuit()
            return []
