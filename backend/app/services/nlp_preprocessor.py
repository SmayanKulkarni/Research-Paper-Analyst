"""
nlp_preprocessor.py

Apply NLP techniques (abstractive summarization, key-phrase extraction, entity recognition)
to research papers BEFORE they are passed to LLMs to optimize token usage.

Uses lightweight transformers models and fallback regex patterns.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from app.utils.logging import logger


def extract_key_phrases(text: str, max_phrases: int = 10) -> List[str]:
    """
    Extract key phrases/terms from text using simple heuristics and regex.
    
    Fallback for when transformers not available:
    - Capitalized phrases
    - Words appearing frequently
    - Technical terms (words followed by common suffixes)
    
    Returns list of (phrase, score) tuples sorted by score.
    
    Note: To skip KeyBERT model download, set env var SKIP_NLP_MODELS=true.
    """
    import os
    
    # Allow skipping transformers downloads
    if os.getenv("SKIP_NLP_MODELS", "false").lower() != "true":
        # Try using transformers KeyBERT if available
        try:
            from keybert import KeyBERT
            kw_model = KeyBERT()
            keywords = kw_model.extract_keywords(text, language="english", top_n=max_phrases)
            return [kw[0] for kw in keywords]
        except Exception as e:
            logger.debug(f"KeyBERT extraction failed: {e}; falling back to regex patterns")
    
    # Fallback: regex-based extraction
    phrases: Dict[str, int] = {}
    
    # Pattern 1: Capitalized phrases (likely proper nouns or technical terms)
    capitalized_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    for match in re.finditer(capitalized_pattern, text):
        phrase = match.group(0)
        if len(phrase) > 2:  # Skip very short phrases
            phrases[phrase] = phrases.get(phrase, 0) + 1
    
    # Pattern 2: Common technical terms (words ending in -tion, -ism, -ment)
    technical_pattern = r'\b\w+(?:tion|ism|ment|ing|ical|ous)\b'
    for match in re.finditer(technical_pattern, text, re.IGNORECASE):
        phrase = match.group(0)
        if len(phrase) > 4:
            phrases[phrase] = phrases.get(phrase, 0) + 1
    
    # Sort by frequency
    sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
    return [p[0] for p in sorted_phrases[:max_phrases]]


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract named entities (persons, organizations, locations, etc.) from text.
    
    Uses spaCy if available; fallback to regex patterns.
    """
    entities: Dict[str, List[str]] = {
        "PERSON": [],
        "ORG": [],
        "GPE": [],
        "OTHER": [],
    }
    
    # Try spaCy
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.debug("spaCy model not found; using regex fallback")
            nlp = None
        
        if nlp:
            doc = nlp(text[:10000])  # Limit to first 10k chars for speed
            for ent in doc.ents:
                if ent.label_ in entities:
                    entities[ent.label_].append(ent.text)
                else:
                    entities["OTHER"].append(ent.text)
            
            # Deduplicate
            for key in entities:
                entities[key] = list(set(entities[key]))
            
            return entities
    except Exception as e:
        logger.debug(f"spaCy entity extraction failed: {e}; using regex fallback")
    
    # Fallback regex patterns
    # Pattern: Dr., Prof., Dr., etc. followed by name
    person_pattern = r'(?:Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
    for match in re.finditer(person_pattern, text):
        entities["PERSON"].append(match.group(1))
    
    # Pattern: University of X, X University
    org_pattern = r'(?:\w+\s+)?[Uu]niversity(?:\s+of\s+\w+)?|(?:\w+\s+)+(?:Lab|Institute|Corporation|Inc\.)'
    for match in re.finditer(org_pattern, text):
        entities["ORG"].append(match.group(0))
    
    # Deduplicate
    for key in entities:
        entities[key] = list(set(entities[key]))[:10]  # Limit to 10 per category
    
    return entities


def abstractive_summarize(text: str, max_length: int = 200, min_length: int = 50) -> str:
    """
    Create an abstractive summary of the text using transformers.
    
    Uses Hugging Face transformers (facebook/bart-large-cnn) if available.
    Fallback: extractive summary using sentence importance.
    
    Note: First call will download ~1.34GB model; set env var SKIP_NLP_MODELS=true to disable.
    """
    import os
    
    # Allow skipping transformers downloads
    if os.getenv("SKIP_NLP_MODELS", "false").lower() == "true":
        logger.debug("Skipping abstractive summarization (SKIP_NLP_MODELS=true); using extractive fallback")
        # Fall through to extractive summary
    else:
        # Try transformers
        try:
            from transformers import pipeline
            summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            
            # Limit input to ~1000 chars to avoid timeout
            input_text = text[:2000]
            summary = summarizer(input_text, max_length=max_length, min_length=min_length, do_sample=False)
            return summary[0]["summary_text"]
        except Exception as e:
            logger.debug(f"Abstractive summarization failed: {e}; using extractive fallback")
    
    # Fallback: extractive summary
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if not sentences:
        return text[:max_length]
    
    # Simple: take first 3-5 sentences
    num_sentences = min(3, len(sentences))
    summary = ". ".join(sentences[:num_sentences]) + "."
    
    return summary[:max_length]


def preprocess_research_paper(
    text: str,
    enable_summarization: bool = True,
    enable_key_phrases: bool = True,
    enable_entities: bool = False,
    max_output_length: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Apply NLP preprocessing to a research paper before LLM analysis.
    
    Returns a dict with:
    {
        "original_text": str,
        "processed_text": str,  # Summary + extracted info
        "summary": str,
        "key_phrases": List[str],
        "entities": Dict[str, List[str]],
        "token_savings": int,  # Estimated tokens saved vs original
    }
    """
    original_length = len(text)
    
    result: Dict[str, Any] = {
        "original_text": text,
        "processed_text": "",
        "summary": "",
        "key_phrases": [],
        "entities": {},
        "token_savings_estimate": 0,
    }
    
    processed_parts: List[str] = []
    
    # Step 1: Summarization
    if enable_summarization:
        try:
            summary = abstractive_summarize(text)
            result["summary"] = summary
            processed_parts.append(f"SUMMARY:\n{summary}\n")
        except Exception as e:
            logger.warning(f"Summarization step failed: {e}")
            processed_parts.append(text[:1000])  # Fallback: first 1000 chars
    
    # Step 2: Key phrase extraction
    if enable_key_phrases:
        try:
            key_phrases = extract_key_phrases(text)
            result["key_phrases"] = key_phrases
            processed_parts.append(f"\nKEY CONCEPTS: {', '.join(key_phrases)}\n")
        except Exception as e:
            logger.warning(f"Key phrase extraction failed: {e}")
    
    # Step 3: Entity extraction
    if enable_entities:
        try:
            entities = extract_entities(text)
            result["entities"] = entities
            entity_str = "\n".join([
                f"{key}: {', '.join(vals[:3])}"  # Limit to 3 per category
                for key, vals in entities.items() if vals
            ])
            if entity_str:
                processed_parts.append(f"\nENTITIES:\n{entity_str}\n")
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
    
    # Combine processed text
    processed_text = "\n".join(processed_parts)
    
    # Step 4: Truncate if needed
    if max_output_length and len(processed_text) > max_output_length:
        processed_text = processed_text[:max_output_length] + "\n[... content truncated for token efficiency ...]"
    
    result["processed_text"] = processed_text
    
    # Estimate token savings
    # Rough estimate: 1 token ≈ 4 characters
    original_tokens = len(text) / 4
    processed_tokens = len(processed_text) / 4
    result["token_savings_estimate"] = max(0, int(original_tokens - processed_tokens))
    
    logger.info(
        f"NLP preprocessing: {original_length} chars → {len(processed_text)} chars "
        f"(est. ~{result['token_savings_estimate']} tokens saved)"
    )
    
    return result


def preprocess_for_chunk_compression(
    text: str,
    summary_length: int = 100,
) -> str:
    """
    Lightweight preprocessing for text chunks before compression.
    
    Returns a condensed version suitable for token-efficient compression.
    """
    # Extract key info without full NLP (faster)
    lines = text.split('\n')
    
    # Remove empty lines and extremely long lines
    lines = [l.strip() for l in lines if l.strip() and len(l) < 500]
    
    # Take first N lines (usually contains most important info in academic papers)
    key_lines = lines[:10]
    
    condensed = '\n'.join(key_lines)
    
    # Estimate savings
    savings = max(0, (len(text) - len(condensed)) // 4)
    logger.debug(f"Chunk preprocessing: {len(text)} chars → {len(condensed)} chars (~{savings} tokens saved)")
    
    return condensed
