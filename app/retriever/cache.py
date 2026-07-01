"""In-memory LRU retrieval cache with SHA-256 keying and TTL expiration."""

import hashlib
import json
import logging
import time
from collections import OrderedDict

from app.retriever.models import CacheEntry, RetrievalResult, SearchQuery

logger = logging.getLogger(__name__)


def _make_cache_key(query: SearchQuery) -> str:
    """Generates a deterministic SHA-256 cache key from a SearchQuery.

    Args:
        query: The search query to key.

    Returns:
        A hex SHA-256 digest string.
    """
    # Serialize the query to a stable JSON string for hashing
    payload = json.dumps(query.model_dump(), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RetrievalCache:
    """Thread-safe in-memory LRU cache for retrieval results.

    Entries expire after TTL seconds and are evicted when max_size is reached
    using LRU (least-recently-used) eviction.
    """

    def __init__(self, max_size: int = 200, ttl_seconds: float = 3600.0) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    def get(self, query: SearchQuery) -> RetrievalResult | None:
        """Retrieves a cached result for the given query.

        Args:
            query: The search query to look up.

        Returns:
            The cached RetrievalResult if present and valid, else None.
        """
        key = _make_cache_key(query)
        entry = self._store.get(key)

        if entry is None:
            self._misses += 1
            logger.debug("Cache MISS for key %s...", key[:12])
            return None

        # Check TTL expiry
        age = time.time() - entry.cached_at
        if age > entry.ttl_seconds:
            self._store.pop(key, None)
            self._misses += 1
            logger.debug("Cache EXPIRED for key %s... (age=%.1fs)", key[:12], age)
            return None

        # LRU: move to end (most recently used)
        self._store.move_to_end(key)
        entry.hits += 1
        self._hits += 1
        logger.debug("Cache HIT for key %s... (hits=%d)", key[:12], entry.hits)
        return entry.result

    def set(self, query: SearchQuery, result: RetrievalResult) -> None:
        """Stores a result in the cache under the given query key.

        Args:
            query: The search query key.
            result: The retrieval result to cache.
        """
        key = _make_cache_key(query)

        if key in self._store:
            # Update existing entry and move to end
            self._store.move_to_end(key)
            self._store[key] = CacheEntry(
                result=result,
                cached_at=time.time(),
                ttl_seconds=self.ttl_seconds,
            )
            return

        # Evict oldest entry if at capacity
        if len(self._store) >= self.max_size:
            evicted_key, _ = self._store.popitem(last=False)
            self._evictions += 1
            logger.debug("Cache EVICT (LRU): key %s...", evicted_key[:12])

        self._store[key] = CacheEntry(
            result=result,
            cached_at=time.time(),
            ttl_seconds=self.ttl_seconds,
        )
        logger.debug("Cache SET: key %s... (size=%d)", key[:12], len(self._store))

    def invalidate(self, query: SearchQuery) -> bool:
        """Removes a specific entry from the cache.

        Args:
            query: The query whose cached result should be removed.

        Returns:
            True if the key existed and was removed, False otherwise.
        """
        key = _make_cache_key(query)
        if key in self._store:
            self._store.pop(key)
            logger.debug("Cache INVALIDATED: key %s...", key[:12])
            return True
        return False

    def clear(self) -> None:
        """Clears all cache entries."""
        count = len(self._store)
        self._store.clear()
        logger.info("Cache CLEARED: removed %d entries.", count)

    def stats(self) -> dict[str, int | float]:
        """Returns cache performance statistics.

        Returns:
            Dict with total_entries, hits, misses, hit_rate, evictions.
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "total_entries": len(self._store),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": self._evictions,
        }

    def prune_expired(self) -> int:
        """Removes all expired entries from the cache.

        Returns:
            Number of entries pruned.
        """
        now = time.time()
        expired_keys = [
            k for k, entry in self._store.items()
            if (now - entry.cached_at) > entry.ttl_seconds
        ]
        for k in expired_keys:
            self._store.pop(k, None)
        if expired_keys:
            logger.debug("Cache PRUNE: removed %d expired entries.", len(expired_keys))
        return len(expired_keys)
