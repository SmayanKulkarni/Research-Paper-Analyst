"""Token budget tracking and rate-limit mitigation.

Tracks per-analysis token usage to gracefully degrade when approaching Groq TPM limits.
Includes per-agent and per-analysis metrics for detailed monitoring.
"""
import time
import threading
from threading import Lock
from typing import Dict, List, Optional
from collections import defaultdict
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
    """Track token usage with per-agent and per-analysis metrics."""
    
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
        
        # Per-agent and per-analysis metrics
        self.per_agent_usage: Dict[str, int] = defaultdict(int)  # agent_name -> tokens
        self.per_agent_calls: Dict[str, int] = defaultdict(int)  # agent_name -> call count
        self.per_analysis_metrics: Dict[str, dict] = {}  # analysis_id -> { estimated, actual, agents, ... }
        self.current_analysis_id: Optional[str] = None
    
    def add_usage(self, tokens: int, agent_name: Optional[str] = None):
        """Record token usage, optionally attributed to an agent."""
        with self.lock:
            self.tokens_used += tokens
            
            if agent_name:
                self.per_agent_usage[agent_name] += tokens
                self.per_agent_calls[agent_name] += 1
            
            remaining = self.safety_threshold - self.tokens_used
            if remaining < 0:
                logger.warning(
                    f"Token budget exceeded: used {self.tokens_used}/{self.safety_threshold}. "
                    f"Graceful degradation active."
                )
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
    
    def start_analysis(self, analysis_id: str):
        """Mark the start of a new analysis session for per-analysis tracking."""
        with self.lock:
            self.current_analysis_id = analysis_id
            self.per_analysis_metrics[analysis_id] = {
                "estimated_tokens": 0,
                "actual_tokens": 0,
                "start_time": time.time(),
                "end_time": None,
                "agents_used": set(),
                "status": "in_progress",
            }
    
    def end_analysis(self, analysis_id: str):
        """Mark the end of an analysis session."""
        with self.lock:
            if analysis_id in self.per_analysis_metrics:
                self.per_analysis_metrics[analysis_id]["end_time"] = time.time()
                self.per_analysis_metrics[analysis_id]["status"] = "complete"
    
    def record_agent_call(self, analysis_id: str, agent_name: str, estimated_tokens: int, actual_tokens: int):
        """Record a specific agent call with token estimates and actuals."""
        with self.lock:
            if analysis_id in self.per_analysis_metrics:
                metrics = self.per_analysis_metrics[analysis_id]
                metrics["estimated_tokens"] += estimated_tokens
                metrics["actual_tokens"] += actual_tokens
                metrics["agents_used"].add(agent_name)
                
                # Log divergence if significant
                if actual_tokens > estimated_tokens * 1.2:
                    logger.warning(
                        f"Agent '{agent_name}' token estimate underestimated: "
                        f"estimated={estimated_tokens}, actual={actual_tokens}"
                    )
    
    def get_per_agent_summary(self) -> Dict[str, dict]:
        """Get summary of token usage per agent."""
        with self.lock:
            summary = {}
            for agent_name, tokens in self.per_agent_usage.items():
                calls = self.per_agent_calls.get(agent_name, 1)
                summary[agent_name] = {
                    "total_tokens": tokens,
                    "call_count": calls,
                    "avg_tokens_per_call": tokens // max(1, calls),
                }
            return summary
    
    def get_analysis_metrics(self, analysis_id: str) -> Optional[Dict]:
        """Get detailed metrics for a specific analysis."""
        with self.lock:
            return self.per_analysis_metrics.get(analysis_id)
    
    def log_analysis_summary(self, analysis_id: str):
        """Log a detailed summary of an analysis."""
        with self.lock:
            metrics = self.per_analysis_metrics.get(analysis_id)
            if not metrics:
                return
            
            duration = (metrics.get("end_time") or time.time()) - metrics.get("start_time", time.time())
            estimated = metrics.get("estimated_tokens", 0)
            actual = metrics.get("actual_tokens", 0)
            accuracy = 0
            if estimated > 0:
                accuracy = (actual / estimated) * 100
            
            logger.info(
                f"Analysis {analysis_id} summary: "
                f"Duration={duration:.1f}s, "
                f"Estimated tokens={estimated}, Actual={actual} ({accuracy:.0f}% accuracy), "
                f"Agents used={sorted(metrics.get('agents_used', set()))}"
            )
    
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
