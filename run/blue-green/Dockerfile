FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set default deployment type
ENV DEPLOYMENT=Stable
ENV PORT=8080

# Copy application code and templates
COPY app.py .
COPY templates templates/

# Use gunicorn with explicit debug logging
CMD exec gunicorn --bind "0.0.0.0:$PORT" --workers 1 --threads 8 --timeout 0 --log-level debug app:app