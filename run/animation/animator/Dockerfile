FROM python:3.9-slim

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
    && rm -rf /var/lib/apt/lists/*

# Download and install specific Blender version
RUN wget https://download.blender.org/release/Blender2.93/blender-2.93.9-linux-x64.tar.xz \
    && tar -xf blender-2.93.9-linux-x64.tar.xz \
    && mv blender-2.93.9-linux-x64 /usr/local/blender \
    && rm blender-2.93.9-linux-x64.tar.xz

# Add Blender to PATH
ENV PATH="/usr/local/blender:${PATH}"

# Create non-root user and setup directories
RUN useradd -m -s /bin/bash blenderuser && \
    mkdir -p /tmp/blender-config && \
    chmod -R 777 /tmp && \
    chown -R blenderuser:blenderuser /tmp && \
    chown -R blenderuser:blenderuser /usr/local/blender

# Set Blender environment variables
ENV BLENDER_USER_CONFIG=/tmp/blender-config
ENV BLENDER_USER_SCRIPTS=/usr/local/blender/2.93/scripts
ENV BLENDER_SYSTEM_SCRIPTS=/usr/local/blender/2.93/scripts
ENV XDG_CONFIG_HOME=/tmp/blender-config

USER blenderuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
ENV PATH="/home/blenderuser/.local/bin:${PATH}"

COPY . .
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app