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

# Clean up Blender safely by selectively removing non-essential files
RUN cd /blender-4.3.0-linux-x64 && \
    # Remove addons, templates, and localization data
    rm -rf 4.3/scripts/addons/* && \
    rm -rf 4.3/scripts/addons_contrib/* && \
    rm -rf 4.3/scripts/templates* && \
    rm -rf 4.3/datafiles/locale/* && \
    # Keep only necessary fonts
    mkdir -p /tmp/fonts && \
    if [ -f "4.3/datafiles/fonts/Inter.woff2" ]; then \
    cp 4.3/datafiles/fonts/Inter.woff2 /tmp/fonts/; \
    fi && \
    if [ -f "4.3/datafiles/fonts/DejaVuSansMono.woff2" ]; then \
    cp 4.3/datafiles/fonts/DejaVuSansMono.woff2 /tmp/fonts/; \
    fi && \
    rm -rf 4.3/datafiles/fonts/* && \
    cp -a /tmp/fonts/* 4.3/datafiles/fonts/ 2>/dev/null || true && \
    # Remove documentation and preview files
    rm -rf 4.3/datafiles/doc/* && \
    rm -rf 4.3/datafiles/preview/* && \
    # Clean Python lib directories (keep core Blender modules)
    find 4.3/python -name "test" -type d -exec rm -rf {} \; 2>/dev/null || true && \
    find 4.3/python -name "tests" -type d -exec rm -rf {} \; 2>/dev/null || true && \
    find 4.3/python -name "__pycache__" -type d -exec rm -rf {} \; 2>/dev/null || true && \
    find 4.3/python -name "*.pyc" -delete && \
    # Remove pip, setuptools, and other non-essential tools
    rm -rf 4.3/python/lib/python3.11/site-packages/pip* 2>/dev/null || true && \
    rm -rf 4.3/python/lib/python3.11/site-packages/setuptools* 2>/dev/null || true && \
    rm -rf 4.3/python/lib/python3.11/site-packages/wheel* 2>/dev/null || true && \
    rm -rf 4.3/python/lib/python3.11/ensurepip 2>/dev/null || true && \
    rm -rf 4.3/python/lib/python3.11/idlelib 2>/dev/null || true && \
    # Remove examples, benchmarks and testing directories
    find 4.3 -type d -name "examples" -exec rm -rf {} \; 2>/dev/null || true && \
    find 4.3 -type d -name "benchmarks" -exec rm -rf {} \; 2>/dev/null || true

# Runtime stage - use slim-bookworm to minimize base size
FROM python:3.9-slim-bookworm as runtime

# Install runtime dependencies in a single layer to minimize size
# Install only what's proven to be needed for Blender to run
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libxi6 \
    libxfixes3 \
    libxrender1 \
    libxcb1 \
    libx11-6 \
    libxkbcommon0 \
    libxxf86vm1 \
    libxcursor1 \
    libsm6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Prepare the filesystem before copying Blender
RUN mkdir -p /usr/local/blender /app /tmp/blender-config \
    && useradd -m -s /bin/bash blenderuser \
    && chown -R blenderuser:blenderuser /usr/local/blender /app /tmp

# Copy the cleaned Blender files from builder stage
COPY --from=builder --chown=blenderuser:blenderuser /blender-4.3.0-linux-x64 /usr/local/blender

# Switch to non-root user for security
USER blenderuser
WORKDIR /app

# Copy requirements and install dependencies with cleanup
COPY --chown=blenderuser:blenderuser requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt \
    && find ~/.local -name '*.pyc' -delete \
    && find ~/.local -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true \
    && rm -rf ~/.cache/pip

# Set environment variables - minimize redundant paths
ENV PATH="/usr/local/blender:/home/blenderuser/.local/bin:${PATH}" \
    BLENDER_USER_CONFIG=/tmp/blender-config \
    BLENDER_USER_SCRIPTS=/usr/local/blender/4.3/scripts \
    BLENDER_SYSTEM_SCRIPTS=/usr/local/blender/4.3/scripts \
    XDG_CONFIG_HOME=/tmp/blender-config \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy only necessary application files (minimize what's copied)
COPY --chown=blenderuser:blenderuser . .

# Command to run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app