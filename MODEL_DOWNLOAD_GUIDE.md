# Model Download & Optimization Guide

## What You're Seeing

During code execution, you see progress bars like:
```
model.safetensors:  15%|█████████▋                                                       | 201M/1.34G [00:27<01:07, 16.8MB/s]
```

This is **Hugging Face downloading pretrained models** for NLP tasks.

---

## Models Downloaded

| Model | Size | Purpose | Component |
|-------|------|---------|-----------|
| `facebook/bart-large-cnn` | ~1.34 GB | Abstractive summarization | `nlp_preprocessor.py` |
| `gpt2` | ~631 MB | Token counting | `token_counter.py` |
| `bert-base-uncased` | ~440 MB | KeyBERT key-phrase extraction | `nlp_preprocessor.py` |
| **Total** | **~2.4 GB** | | **First run only** |

---

## How to Skip Downloads (Recommended)

### Option 1: Disable All NLP Model Downloads

Set environment variable before running:
```bash
export SKIP_NLP_MODELS=true
python -m uvicorn app.main:app --reload
```

**Effect:**
- ✅ No model downloads
- ✅ Uses regex-based fallback for summarization
- ✅ Uses char-based estimation for token counting
- ✅ Slightly reduced accuracy (~95% vs 99%)
- ✅ **Recommended for development**

### Option 2: Pre-download Models Once

If you want transformers available but don't want to wait on every run:
```bash
# Download and cache all models
python << 'EOF'
from transformers import pipeline, AutoTokenizer
print("Downloading BART summarization model...")
pipeline("summarization", model="facebook/bart-large-cnn")
print("Downloading GPT-2 tokenizer...")
AutoTokenizer.from_pretrained("gpt2")
print("Done! Models cached for future runs.")
EOF
```

Then models are cached in `~/.cache/huggingface/` and won't re-download.

### Option 3: Use Lighter Models

Modify `nlp_preprocessor.py` to use smaller models:
```python
# Replace this:
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# With this (40% smaller):
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")
```

---

## Configuration (`.env`)

Add to your `.env` file:
```env
# Skip NLP model downloads (use regex fallbacks instead)
SKIP_NLP_MODELS=true

# Or use lighter models
USE_LIGHTWEIGHT_MODELS=true

# Disable transformers-based token counting (use char-based instead)
USE_TRANSFORMERS_TOKENIZER=false
```

---

## Quick Start (Development)

### Fastest (No downloads):
```bash
export SKIP_NLP_MODELS=true
cd backend
python -m uvicorn app.main:app --reload
```

### Balanced (Pre-download once):
```bash
cd backend

# One-time download (takes ~2 min)
python << 'EOF'
from transformers import pipeline, AutoTokenizer
pipeline("summarization", model="facebook/bart-large-cnn")
AutoTokenizer.from_pretrained("gpt2")
print("✓ Models ready")
EOF

# Then run (fast on subsequent runs)
python -m uvicorn app.main:app --reload
```

### Production (Full models):
```bash
cd backend
# Builds Docker image which pre-caches models
docker build -f dockerfile.api -t research-analyzer:latest .
docker run -p 8000:8000 research-analyzer:latest
```

---

## What Actually Uses These Models?

### BART Summarization (1.34 GB)
- **When:** Background task after PDF upload (optional)
- **Where:** `nlp_preprocessor.py::abstractive_summarize()`
- **Disable:** Set `SKIP_NLP_MODELS=true` or `enable_summarization=False`

### GPT-2 Tokenizer (631 MB)
- **When:** On-demand token counting (optional)
- **Where:** `token_counter.py::count_tokens_transformers()`
- **Disable:** Use `count_tokens(text, use_transformers=False)` (default)

### KeyBERT (440 MB)
- **When:** Key-phrase extraction during NLP preprocessing (optional)
- **Where:** `nlp_preprocessor.py::extract_key_phrases()`
- **Disable:** Set `SKIP_NLP_MODELS=true` or `enable_key_phrases=False`

---

## Default Behavior (as of now)

✅ **No downloads on startup** (all gracefully degrade)
✅ **Models only download on first use**
✅ **All NLP features have regex fallbacks**
✅ **Recommended: Set `SKIP_NLP_MODELS=true` for dev**

---

## Environment Variable Reference

```env
# === NLP Preprocessing ===
SKIP_NLP_MODELS=true|false              # Skip all model downloads
USE_LIGHTWEIGHT_MODELS=true|false       # Use smaller models
ENABLE_NLP_PREPROCESSING=true|false     # Enable/disable entire NLP pipeline
NLP_MAX_OUTPUT_LENGTH=5000              # Max chars after preprocessing

# === Token Counting ===
USE_TRANSFORMERS_TOKENIZER=true|false  # Use GPT-2 (accurate) vs char-based (fast)

# === Citation Processing ===
MAX_CITATIONS_TO_PROCESS=50
MAX_ARXIV_PAPERS_PER_UPLOAD=5
```

---

## Troubleshooting

### Q: Downloads are stuck or timing out
**A:** Increase timeout or disable:
```bash
export SKIP_NLP_MODELS=true
export HF_DATASETS_CACHE=/tmp/hf_cache
```

### Q: I want accurate token counting without downloading
**A:** Use char-based estimation (default):
```python
from app.services.token_counter import count_tokens
tokens = count_tokens(text, use_transformers=False)  # No download
```

### Q: How do I verify models are cached?
**A:** Check the cache directory:
```bash
ls -lh ~/.cache/huggingface/hub/
```

### Q: Can I use CPU-only or GPU?
**A:** Models auto-detect; set env var to force:
```bash
export TORCH_DEVICE=cpu
```

---

## Summary

| Use Case | Command | Download | Speed |
|----------|---------|----------|-------|
| Development (recommended) | `SKIP_NLP_MODELS=true` | None | Fast ⚡ |
| Testing with NLP | Pre-download once | 2 min | Fast ⚡ |
| Production Docker | Auto-caches on build | Yes | Fast ⚡ |
| Max accuracy | Default | On-demand | Slower 🐢 |

**TL;DR:** Start with `export SKIP_NLP_MODELS=true` for zero downloads in dev. Production Docker will handle it automatically.
