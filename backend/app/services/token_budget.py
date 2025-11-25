"""Token budget tracking and rate-limit mitigation.

Tracks per-analysis token usage to gracefully degrade when approaching Groq TPM limits.
"""
import time
import threading
from threading import Lock
from typing import Dict
from app.utils.logging import logger
from app.config import get_settings

# Approximate token counts per operation (for estimation, not exact)
TOKEN_ESTIMATES = {
    "compression_per_chunk": 200,  # ~200 tokens per compressed chunk
    "proofreading": 150,  # ~150 tokens for proofreading response
    "citation": 100,  # ~100 tokens for citation check
    "structure": 100,  # ~100 tokens for structure check
    "consistency": 100,  # ~100 tokens for consistency check
    "vision": 200,  # ~200 tokens for vision analysis
    "plagiarism": 50,  # ~50 tokens for plagiarism query
}

class TokenBudgetTracker:
    """Track token usage and provide graceful degradation when approaching limits."""
    
    def __init__(self, tpm_limit: int = 8000, safety_margin: float = 0.8):
        """
        - tpm_limit: tokens per minute limit (Groq default is 8000 for free tier)
        - safety_margin: only use up to this fraction of TPM before triggering degradation (default 80%)
        """
        self.tpm_limit = tpm_limit
        self.safety_margin = safety_margin
        self.safety_threshold = int(tpm_limit * safety_margin)
        self.tokens_used = 0
        self.lock = Lock()
        self.last_reset = time.time()
    
    def add_usage(self, tokens: int):
        """Record token usage."""
        with self.lock:
            self.tokens_used += tokens
            remaining = self.safety_threshold - self.tokens_used
            if remaining < 0:
                logger.warning(f"Token budget exceeded: used {self.tokens_used}/{self.safety_threshold}. Graceful degradation active.")
                return False
            return True
    
    def estimate_tokens(self, operation: str, count: int = 1) -> int:
        """Estimate tokens for an operation."""
        per_unit = TOKEN_ESTIMATES.get(operation, 100)
        return per_unit * count
    
    def check_budget(self, operation: str, count: int = 1) -> bool:
        """Check if operation would exceed budget; return True if ok, False if over."""
        est = self.estimate_tokens(operation, count)
        with self.lock:
            if self.tokens_used + est > self.safety_threshold:
                logger.warning(
                    f"Operation '{operation}' would exceed token budget: "
                    f"current={self.tokens_used}, estimated_for_op={est}, threshold={self.safety_threshold}"
                )
                return False
            return True

    def check_raw_estimate(self, tokens: int) -> bool:
        """Check a raw token estimate (useful when we compute tokens from prompt length).

        Returns True if adding `tokens` would still be within the safety threshold.
        """
        with self.lock:
            if self.tokens_used + tokens > self.safety_threshold:
                logger.debug(
                    f"Raw token estimate would exceed budget: current={self.tokens_used}, estimate={tokens}, threshold={self.safety_threshold}"
                )
                return False
            return True
    
    def reset(self):
        """Reset token counter (call once per minute in production)."""
        with self.lock:
            self.tokens_used = 0
            self.last_reset = time.time()


def _auto_reset_loop(tracker: TokenBudgetTracker, interval: int = 60):
    """Background loop that resets the tracker every `interval` seconds.

    This helps align the in-process counter with Groq's per-minute TPM window.
    Runs as a daemon thread.
    """
    try:
        while True:
            time.sleep(interval)
            tracker.reset()
            logger.debug("TokenBudgetTracker auto-reset executed")
    except Exception:
        logger.exception("TokenBudgetTracker auto-reset loop terminated unexpectedly")

# Global singleton (per-process)
_token_tracker: Dict = {}

def get_token_tracker() -> TokenBudgetTracker:
    """Get or create the global token tracker for this process."""
    if "tracker" not in _token_tracker:
        settings = get_settings()
        tpm = getattr(settings, 'GROQ_TPM_LIMIT', 8000)
        margin = getattr(settings, 'TOKEN_BUDGET_SAFETY_MARGIN', 0.8)
        tracker = TokenBudgetTracker(tpm_limit=tpm, safety_margin=margin)
        _token_tracker["tracker"] = tracker
        # start auto-reset thread (daemon)
        reset_interval = 60
        t = threading.Thread(target=_auto_reset_loop, args=(tracker, reset_interval), daemon=True)
        t.start()
    return _token_tracker["tracker"]
