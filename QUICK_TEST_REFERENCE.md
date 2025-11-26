# PDF Parser Testing - Quick Reference Card

## 🎯 Three Ways to Test

| Method | Time | Command | Use Case |
|--------|------|---------|----------|
| **Basic Test** | 30s | `python test_pdf_parser.py file.pdf` | Verify extraction works |
| **Full Pipeline** | 2-5m | `python test_pipeline.py --full file.pdf` | Test all 6 agents |
| **Code Examples** | 1m | `python examples_pdf_parser.py 0` | Learn integration |

---

## 🚀 Get Started (Copy & Paste)

```bash
# Navigate to backend
cd /home/smayan/Desktop/Research-Paper-Analyst/backend

# Test with sample PDF
python test_pdf_parser.py /home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf

# Test parsing speed
python test_pipeline.py --parse-only

# Run all examples
python examples_pdf_parser.py 0
```

---

## 📊 What Each Test Does

### `test_pdf_parser.py`
```
PDF File → Extract Text → Show Statistics
✅ Validates: Text extraction, character count, word count
⏱️  Time: 1-2 seconds
📝 Output: Text statistics + first 500 chars preview
```

### `test_pipeline.py`
```
PDF File → Extract Text → 6 CrewAI Agents → Results
✅ Validates: Full analysis pipeline, all agents
⏱️  Time: 2-5 minutes (first run), 1-2 minutes (subsequent)
📝 Output: Analysis results in JSON format
```

### `examples_pdf_parser.py`
```
6 Code Examples:
1. Basic parsing
2. Get statistics
3. Split into chunks
4. Extract sentences
5. Search keywords
6. Prepare for analysis
✅ Validates: Integration patterns
⏱️  Time: 1 minute for all
📝 Output: Working code you can copy
```

---

## 💻 Common Commands

```bash
# Test specific PDF
python test_pdf_parser.py /path/to/file.pdf

# Test all PDFs in folder
python test_pdf_parser.py /path/to/folder --batch

# Parse only (fast test)
python test_pipeline.py --parse-only /path/to/file.pdf

# Full pipeline (slow test)
python test_pipeline.py --full /path/to/file.pdf

# Run example 1 (basic)
python examples_pdf_parser.py 1

# Run example 2 (stats)
python examples_pdf_parser.py 2

# Run example 5 (search keywords)
python examples_pdf_parser.py 5

# Run all examples
python examples_pdf_parser.py 0

# Get help
python test_pdf_parser.py --help
python test_pipeline.py --help
```

---

## 📈 Expected Output

### Basic Test Success
```
✅ Parse successful!

📋 Text Statistics:
   - Total characters: 41,755
   - Total words: 6,124
   - Number of lines: 641

✅ All tests passed!
```

### Full Pipeline Success
```
📖 Step 1: Parsing PDF...
✅ PDF parsed successfully

⚙️  Step 2: Running CrewAI analysis...
✅ Analysis completed

{
  "citations": [...],
  "structure": {...},
  ...
}

✅ Full pipeline test passed!
```

---

## 🐛 Common Issues & Fixes

| Problem | Solution |
|---------|----------|
| "No PDF found" | Use full path: `python test_pdf_parser.py /full/path/file.pdf` |
| "ImportError" | Make sure you're in backend dir: `cd backend` |
| "Module not found" | Install deps: `pip install -r requirements.txt` |
| "No text extracted" | Try different PDF (might be scanned image) |
| "Very slow" | First run loads models (~5-10m). Subsequent runs are fast. |

---

## 🔗 Integration Pattern

```python
# In your code:
from app.services.pdf_parser import parse_pdf_to_text_and_images

# Parse PDF
result = parse_pdf_to_text_and_images("paper.pdf")

# Use the data
text = result["text"]
images = result["images"]

# Send to analysis
from app.crew.orchestrator import run_full_analysis
analysis = run_full_analysis(text=text, images=images)
```

---

## 📁 Files in Backend

```
test_pdf_parser.py       ← Basic parsing tests
test_pipeline.py         ← Full pipeline tests  
examples_pdf_parser.py   ← 6 usage examples
TEST_GUIDE.md            ← Detailed guide
PDF_TEST_REFERENCE.md    ← This file
```

---

## ✅ Test Checklist

- [ ] Can parse a PDF file
- [ ] Extracts text correctly
- [ ] Shows accurate statistics
- [ ] Full pipeline runs without errors
- [ ] All 6 agents execute
- [ ] Results are properly formatted

---

## 🎓 Learn By Example

```python
# Run this to see all patterns:
cd backend
python examples_pdf_parser.py 0
```

Then look at the code in `examples_pdf_parser.py` to:
- See how to use the parser
- Understand the return format
- Learn integration patterns
- Copy code for your use case

---

**Ready to test? Start here:**
```bash
cd /home/smayan/Desktop/Research-Paper-Analyst/backend
python test_pdf_parser.py /home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf
```
