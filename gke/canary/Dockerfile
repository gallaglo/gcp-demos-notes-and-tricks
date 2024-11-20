# Use slim Python image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY templates/ templates/

# Create non-root user for security
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set default environment variable (can be overridden at runtime)
ENV DEPLOYMENT=Unknown

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
