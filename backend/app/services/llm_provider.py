from langchain_groq import ChatGroq
from app.config import get_settings
from time import sleep
import time
import math
import re
import random
import threading
from typing import Callable, Any, Optional
from app.utils.logging import logger
from app.services.response_cache import get_response_cache
from app.services.token_budget import get_token_tracker

# CrewAI LLM factory (agents use crewai.LLM objects)
try:
    from crewai import LLM as CrewLLM
except Exception:
    CrewLLM = None  # type: ignore

settings = get_settings()
response_cache = get_response_cache()
_llm_call_semaphore = threading.Semaphore(getattr(settings, 'CREW_MAX_CONCURRENT_LLM_CALLS', 2))

# Provide both a langchain ChatGroq for any LangChain consumers and a CrewAI factory
# Generic Text LLM (LangChain wrapper) - Uses default citation model for backward compatibility
# OPTIMIZED: max_tokens reduced to 1024 for token efficiency
groq_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name=settings.CREW_CITATION_MODEL,  # Default fallback model
    temperature=0.3,
    max_tokens=1600,
)

# Vision LLM (LangChain wrapper) - OPTIMIZED: max_tokens reduced to 500 for vision responses (very minimal summaries)
vision_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name=settings.CREW_VISION_MODEL,
    temperature=0.1,
    max_tokens=500,
)


class CrewLLMWrapper:
    """Lightweight wrapper around CrewLLM that routes .call() through retry/backoff logic and caching.
    
    This ensures:
    1. Groq rate-limit errors (429) are retried with exponential backoff instead of crashing
    2. Identical prompts are cached to avoid redundant API calls
    """
    
    def __init__(self, underlying, cache_enabled: bool = True):
        self._underlying = underlying
        self._cache_enabled = cache_enabled
    
    def call(self, *args, **kwargs):
        # Extract prompt from args/kwargs for caching key and token estimation
        prompt = None
        prompt_text = None
        if args and isinstance(args[0], str):
            prompt_text = args[0]
            prompt = prompt_text[:500]
        elif 'messages' in kwargs:
            messages = kwargs.get('messages', [])
            if messages and isinstance(messages, list) and len(messages) > 0:
                last = messages[-1]
                # messages may be dicts like {'role': 'user', 'content': '...'}
                if isinstance(last, dict):
                    prompt_text = last.get('content', '')
                else:
                    prompt_text = str(last)
                prompt = str(prompt_text)[:500]
        
        # Check cache before calling Groq
        if self._cache_enabled and prompt:
            cached = response_cache.get(prompt, model=getattr(self._underlying, 'model', 'unknown'))
            if cached is not None:
                return cached

        # Estimate token usage for this call (very rough: 4 chars ~ 1 token)
        def estimate_tokens_from_text(text: Optional[str]) -> int:
            if not text:
                return 150
            # conservative estimate: 1 token per 4 characters
            est = max(50, math.ceil(len(text) / 4))
            # add some overhead for system messages / response
            return est + 64

        tracker = get_token_tracker()
        est_tokens = estimate_tokens_from_text(prompt_text)

        # If this call would exceed our safety threshold, try a brief backoff then downgrade to compression model
        if not tracker.check_raw_estimate(est_tokens):
            logger.warning(f"Token budget low: estimated {est_tokens} tokens would exceed safety threshold. Attempting limited backoff/downgrade.")
            backed_off = False
            # small exponential backoff loop to wait for token budget to free
            for attempt in range(3):
                sleep(1 << attempt)
                if tracker.check_raw_estimate(est_tokens):
                    backed_off = True
                    break
            if not backed_off:
                # Downgrade: use compression LLM for a lower-cost response
                try:
                    if CrewLLM is None:
                        raise RuntimeError("crewai.LLM is not available for compression downgrade")
                    comp_model_name = settings.GROQ_CITATION_MODEL  # Use default citation model as fallback
                    logger.info(f"Downgrading LLM to compression model {comp_model_name} to avoid TPM overflow")
                    raw_comp = CrewLLM(model=comp_model_name, api_key=settings.GROQ_API_KEY, temperature=0.2)
                    # call compression model directly (with retries)
                    result = call_groq_with_retries(raw_comp.call, *args, **kwargs)
                    # account for lower token usage (heuristic)
                    comp_tokens = max(20, int(est_tokens * 0.35))
                    tracker.add_usage(comp_tokens)
                    # cache downgraded result under the same prompt key so next time we hit cache
                    if self._cache_enabled and prompt:
                        response_cache.set(prompt, result, model=getattr(raw_comp, 'model', 'compression'))
                    return result
                except Exception:
                    logger.exception("Compression downgrade failed; falling through to normal call and letting call_groq_with_retries handle any rate-limit")        # Route the heavy call through our retry/backoff helper
            # Respect a process-wide semaphore to limit concurrent LLM calls and avoid TPM spikes
            acquired = False
            try:
                _llm_call_semaphore.acquire()
                acquired = True
                result = call_groq_with_retries(self._underlying.call, *args, **kwargs)
            finally:
                if acquired:
                    try:
                        _llm_call_semaphore.release()
                    except Exception:
                        logger.exception("Failed to release LLM call semaphore")

        # Account for estimated tokens used (best-effort)
        try:
            tracker.add_usage(est_tokens)
        except Exception:
            logger.exception("Failed to record token usage")

        # Store result in cache
        if self._cache_enabled and prompt:
            response_cache.set(prompt, result, model=getattr(self._underlying, 'model', 'unknown'))

        return result
    
    # Delegate all other attributes/methods to the underlying LLM
    def __getattr__(self, name):
        return getattr(self._underlying, name)


def get_crewai_llm(model: Optional[str] = None, temperature: float = 0.3, max_tokens: Optional[int] = None):
    """Return a configured CrewAI LLM instance using settings, wrapped with retry logic.

    - model: optional full model string (e.g. 'groq/openai/gpt-oss-120b'). If omitted, uses settings.CREW_CITATION_MODEL (default)
    - temperature: LLM temperature
    - Note: we intentionally do NOT set max_tokens here to allow the underlying LLM to use defaults,
      but the CrewLLMWrapper will apply backoff-retry on 429 errors. Consider adding max_tokens param if needed.
    """
    if CrewLLM is None:
        raise RuntimeError("crewai.LLM is not available in the environment")

    model_name = model or settings.CREW_CITATION_MODEL  # Default fallback model
    # Ensure model string is crew-prefixed if needed (Settings already provides CREW_* helpers)
    # Pass max_tokens where supported to bound large completions per-agent
    kwargs = dict(model=model_name, api_key=settings.GROQ_API_KEY, temperature=temperature)
    if max_tokens is not None:
        kwargs['max_tokens'] = int(max_tokens)
    raw = CrewLLM(**kwargs)
    return CrewLLMWrapper(raw)


def get_crewai_compression_llm(temperature: float = 0.2):
    """Return a smaller, faster LLM optimized for compression tasks.
    
    Uses citation model by default which is lightweight and efficient.
    """
    if CrewLLM is None:
        raise RuntimeError("crewai.LLM is not available in the environment")
    
    # Use citation model (lightweight) for compression tasks
    model_name = settings.GROQ_CITATION_MODEL
    raw = CrewLLM(model=model_name, api_key=settings.GROQ_API_KEY, temperature=temperature)
    return CrewLLMWrapper(raw)


def get_crewai_vision_llm(model: Optional[str] = None, temperature: float = 0.2):
    """Return a configured vision LLM, wrapped with retry logic."""
    if CrewLLM is None:
        raise RuntimeError("crewai.LLM is not available in the environment")
    model_name = model or settings.CREW_VISION_MODEL
    raw = CrewLLM(model=model_name, api_key=settings.GROQ_API_KEY, temperature=temperature)
    return CrewLLMWrapper(raw)


def call_groq_with_retries(callable_fn: Callable[..., Any], *args, max_retries: int = 5, initial_backoff: float = 1.0, **kwargs) -> Any:
    """Call a Groq/LangChain ChatGroq callable with retry/backoff on rate limit-like errors.

    callable_fn is typically a function or LLM object that is callable (e.g. groq_llm.generate or groq_llm.__call__).
    This is a best-effort helper to reduce failures from transient 429/rate-limit issues.
    """
    backoff = initial_backoff
    # Respect any global provider-requested retry window set by other callers in this process
    global _global_retry_until
    try:
        if _global_retry_until > time.time():
            wait_left = _global_retry_until - time.time()
            jitter = random.uniform(0.1, 0.5)
            logger.info(f"Global retry window active; sleeping {wait_left + jitter:.2f}s before attempting call")
            sleep(wait_left + jitter)
    except NameError:
        # global not set yet
        _global_retry_until = 0.0
    for attempt in range(1, max_retries + 1):
        try:
            return callable_fn(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            lower = msg.lower()
            # If provider suggests a retry-after time, respect it exactly (with tiny jitter)
            # e.g. "Please try again in 38.05s."
            m = re.search(r"try again in\s*([0-9]+(?:\.[0-9]+)?)\s*s", lower)
            if m:
                try:
                    wait = float(m.group(1))
                    # publish global retry window so other concurrent callers pause
                    globals_lock = globals().get("_global_retry_lock")
                    if globals_lock is None:
                        _global_retry_lock = threading.Lock()
                        globals()["_global_retry_lock"] = _global_retry_lock
                    else:
                        _global_retry_lock = globals_lock
                    with _global_retry_lock:
                        _global_retry_until = max(globals().get("_global_retry_until", 0.0), time.time() + wait)
                    # add small randomized jitter to avoid thundering herd
                    jitter = random.uniform(0.2, 1.0)
                    wait_time = wait + jitter
                    if attempt < max_retries:
                        logger.warning(f"Groq requested retry-after={wait}s. Sleeping {wait_time:.2f}s before retry (attempt {attempt}/{max_retries}).")
                        sleep(wait_time)
                        continue
                except Exception:
                    # fall through to generic handling
                    logger.debug("Failed to parse provider suggested wait time; falling back to exponential backoff")

            # Generic rate-limit detection (fallback)
            if "429" in lower or "rate" in lower or "rate limit" in lower:
                if attempt < max_retries:
                    logger.warning(f"Groq rate limit detected (attempt {attempt}/{max_retries}). Backing off {backoff}s.")
                    sleep(backoff + random.uniform(0.1, 0.5))
                    backoff *= 2
                    continue
            # not a rate limit or out of retries -> re-raise
            raise

