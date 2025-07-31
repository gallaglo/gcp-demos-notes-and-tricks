FROM python:3.10-slim

WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY adk_main.py .
COPY adk_agents.py .
COPY adk_tools.py .
COPY prompts.py .
COPY main.py .
COPY animation_graph.py .

# Command to run the ADK-based application
CMD ["python", "-m", "uvicorn", "adk_main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]