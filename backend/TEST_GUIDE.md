# PDF Parser Testing Guide

Two test scripts are available to test the PDF parsing functionality:

## 1. Basic PDF Parser Test (`test_pdf_parser.py`)

**Purpose:** Test just the PDF text extraction functionality

**Quick Start:**
```bash
# Test with first available PDF
python test_pdf_parser.py

# Test specific PDF
python test_pdf_parser.py /path/to/document.pdf

# Test all PDFs in directory
python test_pdf_parser.py /path/to/pdf/folder --batch
```

**What it tests:**
- ✅ PDF file can be opened
- ✅ Text is extracted correctly
- ✅ Character/word/line counts
- ✅ Returns proper data structure: `{"text": str, "images": []}`

**Output Example:**
```
✅ Parse successful!

📋 Text Statistics:
   - Total characters: 45,230
   - Total words: 8,124
   - Number of lines: 892
   - Images found: 0

📄 First 500 characters of extracted text:
   ---
   Introduction...
   ---
```

---

## 2. Full Pipeline Test (`test_pipeline.py`)

**Purpose:** Test the complete analysis pipeline (Parse → 6 Agents)

**Quick Start:**
```bash
# Test parsing only (fast - 10-30 seconds)
python test_pipeline.py --parse-only

# Test full pipeline (slow - 2-5 minutes)
python test_pipeline.py --full

# Test specific PDF
python test_pipeline.py --parse-only /path/to/paper.pdf
python test_pipeline.py --full /path/to/paper.pdf
```

**What it tests:**
- ✅ PDF extraction works
- ✅ CrewAI orchestration initializes
- ✅ All 6 agents execute properly:
  - Citation Agent (extracts citations)
  - Structure Agent (analyzes document structure)
  - Consistency Agent (checks internal consistency)
  - Plagiarism Agent (checks for plagiarism)
  - Proofreader Agent (checks grammar/style)
  - Vision Agent (analyzes images/diagrams)
- ✅ Results are properly formatted

**Output Example:**
```
📖 Step 1: Parsing PDF...
✅ PDF parsed successfully
   - Characters extracted: 45,230
   - Words: 8,124

⚙️  Step 2: Running CrewAI analysis pipeline...
✅ Analysis completed

Analysis Results:
{
  "citations": [...],
  "structure": {...},
  "consistency": {...},
  ...
}

✅ Full pipeline test passed!
```

---

## Sample Workflow

### 1. Start with parsing test (validate extraction):
```bash
cd backend
python test_pdf_parser.py research_paper.pdf
```

### 2. If parsing works, test full pipeline:
```bash
python test_pipeline.py --parse-only research_paper.pdf
```

### 3. If everything works, test with full analysis:
```bash
python test_pipeline.py --full research_paper.pdf
```

---

## Troubleshooting

### "No PDF files found"
- Place a PDF in: `/home/smayan/Desktop/Research-Paper-Analyst/backend/storage/uploads/`
- Or provide the path directly: `python test_pdf_parser.py /full/path/to/file.pdf`

### "ImportError: cannot import name..."
- Run tests from the backend directory: `cd backend && python test_*.py`
- Or ensure you're using the correct Python environment with dependencies installed

### PDF parses but shows no text
- Might be a scanned image PDF (not text-based)
- Try a different PDF or convert to text-based format

### Full pipeline is very slow
- First run loads models (5-10 minutes)
- Subsequent runs are faster
- Use `--parse-only` for quick validation

---

## Files Modified

Created two test scripts:
- ✅ `/backend/test_pdf_parser.py` - Basic PDF parsing tests
- ✅ `/backend/test_pipeline.py` - Full pipeline integration tests

Both scripts include:
- Automatic PDF detection
- Detailed output with statistics
- Error handling and debugging info
- Command-line argument support
- Batch processing options
