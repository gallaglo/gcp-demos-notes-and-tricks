# Build stage
FROM python:3.9-slim-bookworm as builder

# Install build dependencies first
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Download and extract Blender - using x64 version for Cloud Run
RUN wget https://download.blender.org/release/Blender4.3/blender-4.3.0-linux-x64.tar.xz \
    && tar -xf blender-4.3.0-linux-x64.tar.xz \
    && rm blender-4.3.0-linux-x64.tar.xz

# Runtime stage
FROM python:3.9-slim-bookworm

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Copy Blender from builder stage
COPY --from=builder /blender-4.3.0-linux-x64 /usr/local/blender

# Clean up unnecessary Blender files, but preserve required ones
RUN rm -rf /usr/local/blender/4.3/scripts/addons/* && \
    rm -rf /usr/local/blender/4.3/scripts/addons_contrib/* && \
    rm -rf /usr/local/blender/4.3/datafiles/locale/* && \
    # Preserve only necessary fonts
    mkdir -p /tmp/fonts && \
    mv /usr/local/blender/4.3/datafiles/fonts/Inter.woff2 /tmp/fonts/ && \
    mv /usr/local/blender/4.3/datafiles/fonts/DejaVuSansMono.woff2 /tmp/fonts/ && \
    rm -rf /usr/local/blender/4.3/datafiles/fonts/* && \
    mv /tmp/fonts/* /usr/local/blender/4.3/datafiles/fonts/ && \
    rmdir /tmp/fonts && \
    # Preserve color management files
    rm -rf /usr/local/blender/4.3/datafiles/preview/* && \
    # Remove documentation if present
    rm -rf /usr/local/blender/4.3/datafiles/doc/* && \
    # Remove any backup files
    find /usr/local/blender -name "*.pyc" -delete && \
    find /usr/local/blender -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Create non-root user and setup directories
RUN useradd -m -s /bin/bash blenderuser && \
    mkdir -p /tmp/blender-config && \
    chmod -R 777 /tmp && \
    chown -R blenderuser:blenderuser /tmp && \
    chown -R blenderuser:blenderuser /usr/local/blender

# Switch to non-root user
USER blenderuser
WORKDIR /app

# Copy requirements and install dependencies directly in runtime stage
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Set environment variables
ENV PATH="/usr/local/blender:/home/blenderuser/.local/bin:${PATH}" \
    BLENDER_USER_CONFIG=/tmp/blender-config \
    BLENDER_USER_SCRIPTS=/usr/local/blender/4.3/scripts \
    BLENDER_SYSTEM_SCRIPTS=/usr/local/blender/4.3/scripts \
    XDG_CONFIG_HOME=/tmp/blender-config

# Copy application files
COPY . .

# Command to run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app