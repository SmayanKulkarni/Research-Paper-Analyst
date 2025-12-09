FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential for some python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to cache installation
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variables
# IMPORTANT: You must set API keys in Hugging Face "Settings" -> "Variables"
ENV PYTHONPATH=/app/backend

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Run the Streamlit app
CMD ["streamlit", "run", "frontend/app.py", "--server.port", "7860", "--server.address", "0.0.0.0"]