FROM python:3.10-slim

WORKDIR /app

# Install build dependencies for compilation if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project source code
COPY . .

# Create necessary directories if not present
RUN mkdir -p data/raw data/processed vectorstore

# -----------------------------------------------------------------
# Pre-download BGE embedding model into the image at build time.
# This eliminates the cold-start download delay that causes Railway
# healthchecks to time out on first deployment.
# -----------------------------------------------------------------
ENV SENTENCE_TRANSFORMERS_HOME=/app/models
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    VECTOR_STORE_PATH=/app/vectorstore \
    SENTENCE_TRANSFORMERS_HOME=/app/models

# Expose API server port
EXPOSE 8000

# Health check — give 180s start-period for first boot on cold container
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Start FastAPI application using robust shell script
CMD ["/app/start.sh"]
