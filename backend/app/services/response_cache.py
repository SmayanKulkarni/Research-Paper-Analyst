"""Response caching for LLM calls to avoid duplicate prompt processing.

Uses a simple in-memory cache with TTL. For production, consider using Redis.
"""
import hashlib
import time
from typing import Dict, Optional, Any
from threading import Lock
from app.utils.logging import logger

class CachedResponse:
    def __init__(self, content: Any, ttl_seconds: int = 3600):
        self.content = content
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class ResponseCache:
    """Simple in-memory LLM response cache with TTL."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.cache: Dict[str, CachedResponse] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = Lock()
    
    @staticmethod
    def _hash_prompt(prompt: str, model: str, temperature: float) -> str:
        """Generate a hash key for prompt + model + temperature."""
        key_str = f"{model}:{temperature}:{prompt}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, prompt: str, model: str = "groq_text", temperature: float = 0.3) -> Optional[Any]:
        """Retrieve cached response if available and not expired."""
        key = self._hash_prompt(prompt, model, temperature)
        with self.lock:
            if key in self.cache:
                cached = self.cache[key]
                if not cached.is_expired():
                    logger.debug(f"Cache hit for prompt hash {key[:8]}...")
                    return cached.content
                else:
                    del self.cache[key]
                    logger.debug(f"Cache expired for prompt hash {key[:8]}...")
        return None
    
    def set(self, prompt: str, response: Any, model: str = "groq_text", temperature: float = 0.3) -> None:
        """Store response in cache."""
        key = self._hash_prompt(prompt, model, temperature)
        with self.lock:
            # Simple eviction: if cache is full, clear oldest 10% of entries
            if len(self.cache) >= self.max_size:
                sorted_keys = sorted(
                    self.cache.keys(),
                    key=lambda k: self.cache[k].created_at
                )
                num_to_remove = max(1, self.max_size // 10)
                for k in sorted_keys[:num_to_remove]:
                    del self.cache[k]
                logger.debug(f"Cache eviction: removed {num_to_remove} oldest entries")
            
            self.cache[key] = CachedResponse(response, self.ttl_seconds)
            logger.debug(f"Cached response for prompt hash {key[:8]}...")
    
    def clear(self) -> None:
        """Clear all cached responses."""
        with self.lock:
            size = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared cache ({size} entries)")
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
            }


# Global singleton cache
_response_cache: Dict = {}

def get_response_cache() -> ResponseCache:
    """Get or create the global response cache."""
    if "cache" not in _response_cache:
        _response_cache["cache"] = ResponseCache(max_size=100, ttl_seconds=3600)
    return _response_cache["cache"]
