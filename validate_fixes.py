#!/usr/bin/env python3
"""
Quick validation script to check for common issues:
1. No asyncio.run() calls inside event loops
2. NLP preprocessor has no LLM calls
3. Plagiarism fallback is disabled
"""

import sys
import re

def check_file(filepath, checks):
    """Check a file for patterns."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    issues = []
    for check_name, patterns in checks.items():
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                issues.append(f"  ⚠️  Found: {check_name}")
    
    return issues

# Define checks
checks = {
    "plagiarism.py": {
        "Contains asyncio.run()": [r"asyncio\.run\("],
        "Contains crawl_and_ingest_sync import": [r"from.*web_crawler.*crawl_and_ingest"],
        "Contains LLM calls": [r"groq_llm|call_groq"],
    },
    "nlp_preprocessor.py": {
        "Contains Groq LLM calls": [r"groq|ChatGroq|call_groq"],
        "Contains litellm": [r"litellm|completion"],
    },
}

files_to_check = {
    "backend/app/services/plagiarism.py": checks["plagiarism.py"],
    "backend/app/services/nlp_preprocessor.py": checks["nlp_preprocessor.py"],
}

print("🔍 Validation Report\n")
all_pass = True

for filepath, file_checks in files_to_check.items():
    print(f"📄 {filepath}")
    issues = check_file(filepath, file_checks)
    
    if issues:
        for issue in issues:
            print(issue)
            all_pass = False
    else:
        print("  ✅ All checks passed")
    print()

if all_pass:
    print("✅ All validations passed!")
    sys.exit(0)
else:
    print("❌ Some issues found. See above.")
    sys.exit(1)
