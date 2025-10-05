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
    """Redis-backed cache with local fallback for single-instance deployments."""

    def __init__(self) -> None:
        self.redis_cache = RedisCache(expiration=CHAT_CACHE_EXPIRATION)
        self.local_cache = LocalCache(expiration=CHAT_CACHE_EXPIRATION)
        self._redis_enabled = True
        self._local_attestations: dict[str, dict] = {}

    def _make_key(self, prefix: str, key: str) -> str:
        return f"{MODEL_NAME}:{prefix}:{key}"

    def _set_string(self, key: str, value: str) -> bool:
        if self._redis_enabled:
            try:
                if self.redis_cache.set_string(key, value):
                    return True
                log.warning("Redis unavailable, caching %s locally", key)
            except Exception as exc:  # pragma: no cover
                log.error("Redis set error for %s: %s", key, exc)
                self._redis_enabled = False

        self.local_cache.set(key, value)
        return True

    def _get_string(self, key: str) -> Optional[str]:
        if self._redis_enabled:
            try:
                value = self.redis_cache.get_string(key)
            except Exception as exc:  # pragma: no cover
                log.error("Redis get error for %s: %s", key, exc)
                self._redis_enabled = False
            else:
                if value:
                    return value
        return self.local_cache.get(key)

    def set_chat(self, chat_id: str, chat: str) -> bool:
        key = self._make_key(CHAT_PREFIX, chat_id)
        return self._set_string(key, chat)

    def get_chat(self, chat_id: str) -> Optional[str]:
        key = self._make_key(CHAT_PREFIX, chat_id)
        return self._get_string(key)

    def set_attestation(self, address: str, payload: object) -> bool:
        key = self._make_key(ATTESTATION_PREFIX, address)
        try:
            encoded = json.dumps(payload)
        except Exception as exc:  # pragma: no cover
            log.error("Attestation serialisation error for %s: %s", address, exc)
            return False

        if isinstance(payload, dict):
            self._local_attestations[address] = payload
        return self._set_string(key, encoded)

    def get_attestation(self, address: str) -> Optional[dict]:
        key = self._make_key(ATTESTATION_PREFIX, address)
        raw = self._get_string(key)
        if not raw:
            return self._local_attestations.get(address)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.error("Invalid attestation JSON for %s", address)
            return self._local_attestations.get(address)
        if isinstance(data, dict):
            self._local_attestations[address] = data
        return data

    def get_attestations(self) -> list:
        decoded: list[dict] = []
        if self._redis_enabled:
            try:
                values = self.redis_cache.get_all_values(f"{MODEL_NAME}:{ATTESTATION_PREFIX}")
                for value in values or []:
                    try:
                        item = json.loads(value)
                    except json.JSONDecodeError:
                        log.error("Invalid attestation JSON retrieved from cache")
                        continue
                    if isinstance(item, dict):
                        decoded.append(item)
                        address = item.get("signing_address")
                        if isinstance(address, str):
                            self._local_attestations[address] = item
            except Exception as exc:  # pragma: no cover
                log.error("Error collecting attestations: %s", exc)
                self._redis_enabled = False

        if not decoded:
            decoded = list(self._local_attestations.values())
        return decoded


cache = ChatCache()
