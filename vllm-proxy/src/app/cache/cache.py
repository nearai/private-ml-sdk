import json
import os
from typing import Optional

from app.logger import log

from .local_cache import LocalCache
from .redis import RedisCache

CHAT_CACHE_EXPIRATION = int(os.getenv("CHAT_CACHE_EXPIRATION", "1200"))
MODEL_NAME = os.getenv("MODEL_NAME")
if not MODEL_NAME:
    raise ValueError("MODEL_NAME is not set")

CHAT_PREFIX = "chat"
ATTESTATION_PREFIX = "attestation"


class ChatCache:
    """
    Dual-layer cache: Local + optional Redis for cross-server sharing.

    - Redis enabled: Write-through to both, read from Redis first
    - Redis disabled: Local-only mode
    - Redis fails: Automatic fallback to local, retry on next operation
    """

    def __init__(self) -> None:
        self._local = LocalCache(expiration=CHAT_CACHE_EXPIRATION)
        self._redis = self._init_redis()

    def _init_redis(self) -> Optional[RedisCache]:
        """Initialize Redis only if REDIS_HOST is configured."""
        if not os.getenv("REDIS_HOST"):
            log.info("Redis not configured, using local cache only")
            return None
        return RedisCache(expiration=CHAT_CACHE_EXPIRATION)

    def _make_key(self, prefix: str, key: str) -> str:
        """Build namespaced cache key: model:prefix:key"""
        return f"{MODEL_NAME}:{prefix}:{key}"

    def _write_string(self, key: str, value: str) -> None:
        """Write string to local and optionally to Redis."""
        self._local.set(key, value)

        if self._redis:
            try:
                self._redis.set_string(key, value)
            except Exception as exc:
                log.warning("Redis write failed for %s: %s", key, exc)

    def _read_string(self, key: str) -> Optional[str]:
        """Read string from Redis first, fallback to local."""
        if self._redis:
            try:
                value = self._redis.get_string(key)
                if value:
                    return value
            except Exception as exc:
                log.warning("Redis read failed for %s: %s", key, exc)

        return self._local.get(key)

    # Chat operations

    def set_chat(self, chat_id: str, chat: str) -> None:
        """Store chat completion data."""
        key = self._make_key(CHAT_PREFIX, chat_id)
        self._write_string(key, chat)

    def get_chat(self, chat_id: str) -> Optional[str]:
        """Retrieve chat completion data."""
        key = self._make_key(CHAT_PREFIX, chat_id)
        return self._read_string(key)

    # Attestation operations

    def set_attestation(self, address: str, payload: dict) -> None:
        """Store attestation (auto-serializes to JSON)."""
        key = self._make_key(ATTESTATION_PREFIX, address)
        try:
            value = json.dumps(payload)
            self._write_string(key, value)
        except (TypeError, ValueError) as exc:
            log.error("Failed to serialize attestation for %s: %s", address, exc)

    def get_attestation(self, address: str) -> Optional[dict]:
        """Retrieve attestation (auto-deserializes from JSON)."""
        key = self._make_key(ATTESTATION_PREFIX, address)
        raw = self._read_string(key)
        if not raw:
            return None

        return self._parse_json(raw, f"attestation {address}")

    def get_attestations(self) -> list[dict]:
        """
        Retrieve all attestations for this model (Redis-only feature).

        Returns empty list if Redis not configured or fails.
        """
        if not self._redis:
            return []

        prefix = f"{MODEL_NAME}:{ATTESTATION_PREFIX}"
        try:
            values = self._redis.get_all_values(prefix)
            return self._parse_json_list(values)
        except Exception as exc:
            log.warning("Failed to retrieve attestations from Redis: %s", exc)
            return []

    # JSON helpers

    def _parse_json(self, raw: str, context: str) -> Optional[dict]:
        """Parse JSON string, log error on failure."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.error("Invalid JSON for %s", context)
            return None

    def _parse_json_list(self, raw_values: list[str]) -> list[dict]:
        """Parse list of JSON strings, skip invalid entries."""
        result = []
        for raw in raw_values:
            try:
                item = json.loads(raw)
                if isinstance(item, dict):
                    result.append(item)
            except json.JSONDecodeError:
                log.warning("Skipping invalid JSON in batch parse")
        return result


cache = ChatCache()
