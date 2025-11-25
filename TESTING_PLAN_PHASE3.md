# Testing & Validation Plan - Phase 3

## Current Status ✅

All optimizations implemented:
1. ✅ Token output reduction (max_tokens limits)
2. ✅ Prompt optimization (ask for summaries)
3. ✅ Input truncation (5000 chars)
4. ✅ Compression limiting (10 chunks)
5. ✅ Smaller models (llama-3-8b for compression)
6. ✅ Response caching (TTL + LRU)
7. ✅ Token budget tracking
8. ✅ Retry/backoff (exponential on 429)
9. ✅ **Vision isolation (separate crew)**
10. ✅ HTTPS arXiv API

## Phase 3: Validation & Fine-tuning

### Test 1: Basic Functionality

**Goal**: Verify the system works without crashes

```bash
# Terminal 1: Start server
cd /home/smayan/Desktop/Research-Paper-Analyst/backend
uvicorn app.main:app --reload

# Terminal 2: Run test (in fresh terminal)
cd /home/smayan/Desktop/Research-Paper-Analyst
python3 backend/test_upload_and_analyze.py \
  --pdf /home/smayan/Documents/Data_Redaction_from_Conditional_Generative_Models.pdf \
  --server http://localhost:8000 \
  --wait 12
```

**Expected Logs**:
```
[INFO] Uploading PDF...
[INFO] file_id: ded84e2b-bc5a-4724-89f2-ad7f59341668
[INFO] Waiting 12 seconds for background crawl...
[INFO] Analyzing...
[INFO] Compressing only first X/Y chunks...
[INFO] Truncated analysis text to 5000 chars...
[INFO] Starting crew analysis pipeline...
✓ Proofreader: Completed
✓ Structure: Completed
✓ Consistency: Completed
✓ Citation: Completed
✓ Plagiarism: Completed
[INFO] Running vision analysis separately...
✓ Vision: Completed
[INFO] Analysis complete. Estimated tokens used: XXXX/6400
```

**Expected Result**: JSON response with all fields including `vision_analysis`

---

### Test 2: Error Resilience

**Goal**: Verify graceful handling of vision failures

```bash
# Edit the test to run with enable_vision=False
python3 -c "
import httpx
import json

base_url = 'http://localhost:8000'
pdf_path = '/home/smayan/Documents/Data_Redaction_from_Conditional_Generative_Models.pdf'

# Upload
with open(pdf_path, 'rb') as f:
    r = httpx.post(f'{base_url}/api/uploads/', files={'file': f})
    file_id = r.json()['file_id']
    print(f'✓ Upload: {file_id}')

# Analyze WITHOUT vision
import time; time.sleep(2)

r = httpx.post(f'{base_url}/api/analyze/?file_id={file_id}')
result = r.json()
print(f'✓ Analysis without vision:')
print(json.dumps({k: v for k, v in result.items() if k != 'raw'}, indent=2))
"
```

**Expected Result**: Analysis completes without vision_analysis field

---

### Test 3: Token Tracking

**Goal**: Verify token usage is under control

Monitor in logs:
```
[INFO] Analysis complete. Estimated tokens used: XXXX/6400
```

**Expected Results**:
- First run: 4500-5500 tokens
- Subsequent runs with same paper: 3000-4000 tokens (with cache hits)
- All runs: < 6400 tokens (80% of 8000 TPM)

---

### Test 4: Caching Effectiveness

**Goal**: Verify response cache is working

```bash
# Upload the same paper twice
for i in {1..2}; do
  echo "=== Run $i ==="
  python3 backend/test_upload_and_analyze.py \
    --pdf /home/smayan/Documents/Data_Redaction_from_Conditional_Generative_Models.pdf \
    --server http://localhost:8000 \
    --wait 2
done
```

**Expected Result**: Second run uses fewer tokens (cache hits reduce API calls)

Look for cache logs:
```
[INFO] Cache hit for prompt hash: abc123...
```

---

### Test 5: Different Content

**Goal**: Verify system works with various paper sizes/types

Test with papers of different sizes:
- Small paper (~5 pages)
- Medium paper (~15 pages)
- Large paper (~30+ pages)

```bash
python3 backend/test_upload_and_analyze.py \
  --pdf /path/to/small_paper.pdf \
  --server http://localhost:8000 \
  --wait 12

python3 backend/test_upload_and_analyze.py \
  --pdf /path/to/large_paper.pdf \
  --server http://localhost:8000 \
  --wait 12
```

**Expected**: All complete without errors, tokens scale appropriately

---

### Test 6: Rate Limit Resilience

**Goal**: Verify retry logic handles 429 errors

This happens naturally if you analyze multiple papers rapidly. Monitor logs for:

```
[WARNING] Groq rate limit (429), retrying in X seconds (attempt N/5)
[INFO] Groq call succeeded after retry
```

**Expected**: Retries succeed without crashing

---

### Test 7: Vision Isolation

**Goal**: Confirm vision runs separately with no context

Monitor logs for:
```
[INFO] Starting crew analysis pipeline...
✓ Proofreader: Completed
✓ Structure: Completed
✓ Consistency: Completed
✓ Citation: Completed
✓ Plagiarism: Completed
[INFO] Running vision analysis separately...
✓ Vision: Completed
```

**Key**: Vision task comes AFTER main crew finishes, not during

---

## Metrics to Track

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Upload latency | <1s | Test timestamps |
| Analysis latency | <30s | Test wait time |
| Tokens per analysis | <6400 | Server logs |
| Vision tokens | <1000 | Estimate from response size |
| Cache hit rate | 20-30% | Count cache hit logs |
| Error rate | 0% | Count exceptions |
| Retry success rate | >95% | Count successful retries |

---

## Configuration Validation

### Check environment is set correctly:

```bash
cd /home/smayan/Desktop/Research-Paper-Analyst/backend

# Verify env vars are loaded
python3 -c "
from app.config import get_settings
s = get_settings()
print(f'Text model: {s.GROQ_TEXT_MODEL}')
print(f'Vision model: {s.GROQ_VISION_MODEL}')
print(f'Compression model: {s.GROQ_COMPRESSION_MODEL}')
print(f'TPM limit: {s.GROQ_TPM_LIMIT}')
print(f'Max chunks: {s.MAX_CHUNKS_TO_COMPRESS}')
print(f'Max text length: {s.MAX_ANALYSIS_TEXT_LENGTH}')
"
```

**Expected Output**:
```
Text model: groq/openai/gpt-oss-120b
Vision model: groq/meta-llama/llama-4-scout-17b-16e-instruct
Compression model: groq/llama-3-8b-8192
TPM limit: 8000
Max chunks: 10
Max text length: 5000
```

---

## Quality Assurance Checklist

- [ ] No crashes on normal operation
- [ ] Vision results included in response
- [ ] Token usage < 6400 per analysis
- [ ] Cache hits reduce token usage on repeats
- [ ] Rate limit retries succeed
- [ ] Error handling is graceful
- [ ] Response JSON is valid
- [ ] All 6 agents produce output (or skipped if disabled)
- [ ] Vision task runs after main crew
- [ ] Logs are clear and informative

---

## Fine-tuning Options (If Issues Found)

### If tokens still too high:
```python
# Option 1: Reduce chunks even more
enable_analysis = run_full_analysis(
    file_id=file_id,
    max_chunks_to_compress=5  # Down from 10
)

# Option 2: Skip optional agents
enable_analysis = run_full_analysis(
    file_id=file_id,
    enable_vision=False,        # Skip vision
    enable_plagiarism=False     # Skip plagiarism
)

# Option 3: Further truncate text
# Edit MAX_ANALYSIS_TEXT_LENGTH in .env
```

### If vision fails frequently:
```bash
# Disable vision temporarily
export ENABLE_VISION=false

# Or in code:
result = run_full_analysis(
    file_id=file_id,
    enable_vision=False
)
```

### If cache not effective:
```python
# Monitor cache stats
from app.services.response_cache import get_response_cache

cache = get_response_cache()
print(cache.stats())  # Should show growing size
```

---

## Success Criteria ✅

All of the following must be true:

1. ✅ No "message length" errors
2. ✅ No "rate limit (429)" crashes
3. ✅ Analysis completes in <30 seconds
4. ✅ Token usage <6400 per analysis
5. ✅ Vision results included when images present
6. ✅ Cache hits reduce subsequent analyses
7. ✅ Graceful fallback when vision fails
8. ✅ All agents produce valid output
9. ✅ JSON response is well-formed
10. ✅ No exception traceback visible to user

---

## Next Phase (If All Tests Pass)

1. **Stress Test**: Run 5 analyses in rapid succession
2. **Load Test**: Monitor token usage stays under 8000 TPM
3. **Production Ready**: Deploy to production environment
4. **Monitoring**: Set up alerts for rate limits and token usage

---

## Debug Commands

If something breaks, use these to investigate:

```bash
# Check imports work
python3 -c "from app.crew.orchestrator import run_full_analysis; print('✓ Orchestrator imports')"

# Check LLM factories work
python3 -c "from app.services.llm_provider import get_crewai_llm; llm = get_crewai_llm(); print(f'✓ LLM factory: {llm}')"

# Check cache works
python3 -c "from app.services.response_cache import get_response_cache; c = get_response_cache(); c.set('test', 'result'); print(f'✓ Cache: {c.get(\"test\")}')"

# Check token tracker works
python3 -c "from app.services.token_budget import get_token_tracker; t = get_token_tracker(); print(f'✓ Tracker: {t.tokens_used}/{t.safety_threshold}')"

# Full server test
uvicorn app.main:app --reload  # Should start without errors
```

---

## When Ready to Deploy

```bash
# Final validation
python3 backend/test_upload_and_analyze.py \
  --pdf /path/to/production_paper.pdf \
  --server http://localhost:8000 \
  --wait 15

# Expected: Success with token usage clearly visible in logs
# Expected: Response time 15-25 seconds
# Expected: Token usage 4500-5500

# Then deploy with confidence
```

---

**Ready to test? Start with Test 1 above! 🚀**
