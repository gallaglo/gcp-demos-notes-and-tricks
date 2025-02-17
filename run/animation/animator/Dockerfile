# Use Debian Bookworm slim image which has newer versions of zlib and expat
FROM python:3.9-slim-bookworm

# Install dependencies first
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    libxrender1 \
    libgl1-mesa-glx \
    libxkbcommon0 \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxcb1 \
    libxrandr2 \
    libegl1 \
    libx11-6 \
    libxcursor1 \
    libxinerama1 \
    libglu1-mesa \
    libsm6 \
    zlib1g \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Download and install specific Blender version
RUN wget https://download.blender.org/release/Blender4.3/blender-4.3.0-linux-x64.tar.xz \
    && tar -xf blender-4.3.0-linux-x64.tar.xz \
    && mv blender-4.3.0-linux-x64 /usr/local/blender \
    && rm blender-4.3.0-linux-x64.tar.xz

# Add Blender to PATH
ENV PATH="/usr/local/blender:${PATH}"

# Create non-root user and setup directories
RUN useradd -m -s /bin/bash blenderuser && \
    mkdir -p /tmp/blender-config && \
    chmod -R 777 /tmp && \
    chown -R blenderuser:blenderuser /tmp && \
    chown -R blenderuser:blenderuser /usr/local/blender

# Set Blender environment variables
ENV BLENDER_USER_CONFIG=/tmp/blender-config \
    BLENDER_USER_SCRIPTS=/usr/local/blender/4.3/scripts \
    BLENDER_SYSTEM_SCRIPTS=/usr/local/blender/4.3/scripts \
    XDG_CONFIG_HOME=/tmp/blender-config

# Switch to non-root user
USER blenderuser
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Add local bin to PATH
ENV PATH="/home/blenderuser/.local/bin:${PATH}"

# Copy application files
COPY . .

# Command to run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app