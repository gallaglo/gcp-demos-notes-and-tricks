FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary source code
COPY animation_mcp_server.py .
COPY script_generator.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV BLENDER_SERVICE_URL=${BLENDER_SERVICE_URL:-http://blender-service:8080}
ENV PORT=${PORT:-8000}

# Expose port for MCP server
EXPOSE ${PORT}

# Run the MCP server directly
CMD ["python", "animation_mcp_server.py"]