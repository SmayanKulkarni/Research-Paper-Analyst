#!/bin/bash

# Root project folder
mkdir -p backend
cd backend

# Core env + requirements
touch .env
touch requirements.txt

# Storage folders (local mode)
mkdir -p storage/uploads
mkdir -p storage/images
mkdir -p storage/parquet

# App structure
mkdir -p app
mkdir -p app/models
mkdir -p app/routers
mkdir -p app/services
mkdir -p app/utils
mkdir -p app/crew
mkdir -p app/crew/agents
mkdir -p app/crew/tasks
mkdir -p app/crew/tools

# Python package initialization
touch app/__init__.py
touch app/models/__init__.py
touch app/routers/__init__.py
touch app/services/__init__.py
touch app/utils/__init__.py
touch app/crew/__init__.py
touch app/crew/agents/__init__.py
touch app/crew/tasks/__init__.py
touch app/crew/tools/__init__.py

# Main application files
touch app/main.py
touch app/config.py

# Models
touch app/models/schemas.py

# Routers
touch app/routers/uploads.py
touch app/routers/analyze.py

# Services
touch app/services/pdf_parser.py
touch app/services/llm_groq.py
touch app/services/embeddings.py
touch app/services/pinecone_client.py
touch app/services/parquet_store.py
touch app/services/plagiarism.py
touch app/services/web_crawler.py

# Utils
touch app/utils/logging.py

# Crew Orchestrator
touch app/crew/orchestrator.py

# Crew Agents
touch app/crew/agents/proofreader_agent.py
touch app/crew/agents/structure_agent.py
touch app/crew/agents/citation_agent.py
touch app/crew/agents/consistency_agent.py
touch app/crew/agents/vision_agent.py
touch app/crew/agents/plagiarism_agent.py

# Crew Tasks
touch app/crew/tasks/proofreading_task.py
touch app/crew/tasks/structure_task.py
touch app/crew/tasks/citation_task.py
touch app/crew/tasks/consistency_task.py
touch app/crew/tasks/vision_task.py
touch app/crew/tasks/plagiarism_task.py

# Crew Tools
touch app/crew/tools/pdf_tool.py
touch app/crew/tools/vision_tool.py
touch app/crew/tools/plagiarism
