"""
token_counter.py

Utilities to count and track tokens accurately before LLM calls.
Provides both a simple char-based estimator and transformers-based counter.
"""

from typing import List, Optional
import re
from app.utils.logging import logger


# Simple token estimation constants
# These are calibrated for typical academic text
CHARS_PER_TOKEN = 4.0
PUNCTUATION_FACTOR = 1.1  # Punctuation marks are often separate tokens


def estimate_tokens_simple(text: str) -> int:
    """
    Simple token estimation: characters / 4 (typical ratio for English text).
    
    Fast, works offline, reasonable accuracy for English.
    Slightly overestimates to be conservative.
    """
    if not text:
        return 0
    
    # Count characters
    char_count = len(text)
    
    # Count punctuation/special chars (often get their own tokens)
    punct_count = len(re.findall(r'[!\"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~]', text))
    
    # Estimate: chars/4 + punctuation bonus
    estimated = int(char_count / CHARS_PER_TOKEN) + int(punct_count * 0.3)
    
    return estimated


def count_tokens_transformers(text: str, model_name: str = "gpt2") -> int:
    """
    Use a HuggingFace tokenizer for accurate token counting.
    
    Defaults to GPT-2 tokenizer (lightweight, fast).
    Falls back to simple estimation if transformers not available.
    """
    try:
        from transformers import AutoTokenizer
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokens = tokenizer.tokenize(text)
        return len(tokens)
    except Exception as e:
        logger.debug(f"Transformers tokenization failed ({e}); falling back to simple estimation")
        return estimate_tokens_simple(text)


def count_tokens(text: str, use_transformers: bool = False) -> int:
    """
    Count tokens in text using the most accurate available method.
    
    Args:
        text: Text to count
        use_transformers: If True, use HuggingFace tokenizer (slower but more accurate)
                         If False, use simple char-based estimation (fast)
    
    Returns:
        Estimated or actual token count
    """
    if use_transformers:
        return count_tokens_transformers(text)
    else:
        return estimate_tokens_simple(text)


def count_tokens_in_messages(messages: List[dict], use_transformers: bool = False) -> int:
    """
    Count total tokens in a list of message dicts (typical LLM format).
    
    Assumes messages are like: [{"role": "user", "content": "..."}, ...]
    Adds overhead for message format tokens.
    """
    total = 0
    
    for msg in messages:
        content = msg.get("content", "")
        role = msg.get("role", "")
        
        # Content tokens
        total += count_tokens(content, use_transformers=use_transformers)
        
        # Overhead for role/formatting (typically 2-4 tokens per message)
        total += 3
    
    # Add overhead for message structure itself
    total += 5
    
    return total


def estimate_response_tokens(
    prompt_tokens: int,
    model_name: str = "groq/llama-3.1-8b-instant",
    context_ratio: float = 2.0,
) -> int:
    """
    Estimate expected response token count based on prompt size and model.
    
    Args:
        prompt_tokens: Number of tokens in the prompt
        model_name: LLM model name (used to calibrate estimate)
        context_ratio: Ratio of response size to prompt size (default 2.0 = 2x prompt tokens)
    
    Returns:
        Estimated response tokens
    """
    # Different models tend to produce different response lengths
    if "gpt-4" in model_name:
        context_ratio = 1.5  # GPT-4 is more concise
    elif "llama" in model_name:
        context_ratio = 2.0  # Llama tends to be more verbose
    elif "claude" in model_name:
        context_ratio = 1.8
    
    # Conservative estimate: response is roughly 1.5x-2x the prompt size
    estimated_response = int(prompt_tokens * context_ratio)
    
    return max(50, min(estimated_response, 2000))  # Clamp between 50 and 2000 tokens


def create_token_summary(
    text: str,
    include_response_estimate: bool = True,
    model_name: str = "groq/llama-3.1-8b-instant",
) -> dict:
    """
    Create a comprehensive token analysis dict for logging/monitoring.
    
    Returns:
    {
        "input_chars": int,
        "input_tokens_simple": int,
        "input_tokens_estimated": int,
        "response_tokens_estimate": int,
        "total_tokens_estimate": int,
        "compression_ratio": float,  # chars per token
    }
    """
    char_count = len(text)
    input_tokens_simple = estimate_tokens_simple(text)
    response_tokens = 0
    
    if include_response_estimate:
        response_tokens = estimate_response_tokens(input_tokens_simple, model_name)
    
    return {
        "input_chars": char_count,
        "input_tokens_simple": input_tokens_simple,
        "input_tokens_estimated": input_tokens_simple,  # Same as simple for now
        "response_tokens_estimate": response_tokens,
        "total_tokens_estimate": input_tokens_simple + response_tokens,
        "compression_ratio": char_count / max(1, input_tokens_simple),
        "model": model_name,
    }


def log_token_summary(text: str, context: str = "analysis") -> None:
    """
    Log a token summary for a piece of text to help with monitoring.
    """
    summary = create_token_summary(text)
    logger.info(
        f"[{context}] Token estimate: {summary['input_tokens_simple']} input tokens, "
        f"{summary['response_tokens_estimate']} est. response tokens, "
        f"{summary['total_tokens_estimate']} total (~{summary['compression_ratio']:.1f} chars/token)"
    )
