"""Small compatibility helper that clears OpenAI-related env vars so the app uses GROQ/crewai by default.

Some environments or libraries fall back to OpenAI when an OPENAI_API_KEY is present. This module is imported early
(from `app.main`) to make sure OpenAI keys won't be picked up accidentally.

This file is intentionally tiny and safe to keep in source control.
"""
import os

OPENAI_ENV_VARS = [
    "OPENAI_API_KEY",
    "OPENAI_ORGANIZATION",
    "OPENAI_API_BASE",
    "OPENAI_API_TYPE",
    "OPENAI_API_VERSION",
]

for k in OPENAI_ENV_VARS:
    if k in os.environ:
        # prefer clearing rather than deleting so downstream code that checks os.environ.get() gets None/''
        os.environ[k] = ""
