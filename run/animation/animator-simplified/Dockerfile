# Copy Dockerfile from original animator service and simplify
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libxi6 \
    libxrandr2 \
    libxfixes3 \
    libxcursor1 \
    libxinerama1 \
    libxxf86vm1 \
    libxss1 \
    libxcomposite1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Blender
WORKDIR /tmp
RUN wget -O blender.tar.xz "https://download.blender.org/release/Blender4.2/blender-4.2.1-linux-x64.tar.xz"
RUN tar -xf blender.tar.xz
RUN mv blender-4.2.1-linux-x64 /usr/local/blender
RUN ln -s /usr/local/blender/blender /usr/local/bin/blender
RUN rm blender.tar.xz

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev

# Copy application code
COPY app.py ./

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]