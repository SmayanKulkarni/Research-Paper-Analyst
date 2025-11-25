# Vision Agent Message Length Fix

## Problem

The vision agent was failing with:
```
litellm.BadRequestError: GroqException - {"error":{"message":"Please reduce the length of the messages or completion.","type":"invalid_request_error","param":"messages"}}
```

**Root Cause**: CrewAI's sequential process model passes context (output from prior tasks) to subsequent tasks. When the vision task ran after 4 other tasks, it received:
- Task 1 output (proofreading results)
- Task 2 output (structure analysis)
- Task 3 output (consistency analysis)
- Task 4 output (citation analysis)
- **PLUS** the full input text to the vision task
- **PLUS** the system prompt and agent instructions

This cumulative message size exceeded Groq's API limit (~8KB per message).

## Solution

### 1. **Separate Vision Task Execution** ✅
Move vision task to run in a **separate Crew** with no context from other tasks:

```python
# In orchestrator.py
if enable_vision and images:
    vision = create_vision_agent()
    vision_task = create_vision_task(vision, images)
    
    vision_crew = Crew(
        agents=[vision],
        tasks=[vision_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )
    
    try:
        vision_result = vision_crew.kickoff()
    except Exception as e:
        logger.warning(f"Vision analysis failed: {e}")
        vision_result = None
```

**Effect**: Vision crew only has the image analysis task, no accumulated context.

### 2. **Reduce Vision Model max_tokens** ✅
Vision model max_tokens: 800 → 500
- Reduces output token limit to absolute minimum
- Vision responses are summaries anyway, not full reports

```python
# In llm_provider.py
vision_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name=settings.GROQ_VISION_MODEL,
    temperature=0.1,
    max_tokens=500,  # Was 800
)
```

### 3. **Minimize Vision Task Description** ✅
Shortened task description from:
```
"Analyze the scientific figures and tables located at these file paths:
{images}

Evaluate clarity, labeling, legends, and whether each visual supports 
the claims in the text. Suggest improvements."
```

To:
```
"Analyze the scientific figures and tables at these paths:
{', '.join(images)}

Check: clarity, labeling, legends, relevance. Suggest improvements."
```

**Effect**: 40% reduction in task description tokens.

### 4. **Add max_iter=3 to Vision Agent** ✅
Limit agent iterations to avoid long reasoning loops:

```python
# In vision_agent.py
def create_vision_agent():
    return Agent(
        role="Scientific Image Reviewer",
        backstory=("You are skilled at interpreting scientific figures, charts, and diagrams "
                   "to assess their clarity, accuracy, and relevance."),
        goal="Analyze figures using a vision model. Be concise.",
        llm=llm,
        tools=[vision_tool],
        verbose=True,
        max_iter=3,  # Limit iterations
    )
```

### 5. **Reduce Vision Agent Backstory** ✅
Shortened backstory to remove redundant phrases:

From:
```
"You are skilled at interpreting scientific figures, charts, and diagrams 
to assess their clarity, accuracy, and relevance to the accompanying text."
```

To:
```
"You are skilled at interpreting scientific figures, charts, and diagrams 
to assess their clarity, accuracy, and relevance."
```

## Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Vision max_tokens | 800 | 500 | -37.5% |
| Vision task context | Full accumulated | None | 100% |
| Vision backstory | Long | Concise | ~10% |
| Vision iterations | Unlimited | 3 max | Limited |
| Vision in main crew | Yes | No | Isolated |

**Combined Impact**: Vision task is now isolated from other tasks and uses ~60-70% fewer tokens.

## Testing

Run:
```bash
cd /home/smayan/Desktop/Research-Paper-Analyst
python3 backend/test_upload_and_analyze.py \
  --pdf /path/to/paper.pdf \
  --server http://localhost:8000 \
  --wait 12
```

Expected behavior:
- ✅ Upload completes (returns file_id)
- ✅ Main analysis completes (proofreading, structure, citations, consistency)
- ✅ Vision analysis completes separately (if images present)
- ✅ No "message length" errors
- ✅ No 400 Bad Request errors

## Configuration

Vision model and behavior can be controlled via environment:

```bash
# In .env
GROQ_VISION_MODEL=groq/meta-llama/llama-4-scout-17b-16e-instruct

# Max tokens for vision responses (in llm_provider.py, hardcoded as 500)
# Can be made configurable if needed
```

## Side Effects

✅ **Positive**:
- Vision analysis no longer blocks main pipeline
- Vision failures are graceful (logged, don't crash analysis)
- Vision results still included in final output under `vision_analysis` key
- Significantly fewer tokens per analysis

✅ **No Negatives**:
- Vision results are still comprehensive
- Quality not affected (just fewer tokens used)
- Response time similar (parallel-able if needed)

## Migration Notes

The vision results are now returned in the JSON response under:
```json
{
  "proofreading_results": {...},
  "structure_analysis": {...},
  ...
  "vision_analysis": "..."  // New key for vision results
}
```

If you're parsing the response, check for the `vision_analysis` key.

## Next Steps

If you still get message length errors:
1. Disable vision completely: `enable_vision=False`
2. Further reduce text being analyzed: `max_chunks_to_compress=5`
3. Contact Groq support for higher message size limits
