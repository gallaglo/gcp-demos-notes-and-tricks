# Use Python 3.13 slim as recommended by ADK docs
FROM python:3.13-slim

# Create non-root user for security as recommended
RUN useradd -m -u 1000 adkuser && \
    mkdir -p /app && \
    chown -R adkuser:adkuser /app

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for better caching
COPY --chown=adkuser:adkuser pyproject.toml ./

# Switch to non-root user before installing dependencies
USER adkuser

# Install dependencies using uv
RUN uv sync

# Copy all application code including ADK agent structure
COPY --chown=adkuser:adkuser . .

# Set environment variables recommended by ADK
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GOOGLE_GENAI_USE_VERTEXAI=True

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run the FastAPI application using uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]