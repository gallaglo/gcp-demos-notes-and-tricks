# Stage 1: Build Python dependencies
FROM python:3.9-slim-bookworm as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final image
FROM python:3.9-slim-bookworm

# Install runtime dependencies
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
    # Security updates
    zlib1g \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Download and install specific Blender version
RUN wget https://download.blender.org/release/Blender2.93/blender-2.93.9-linux-x64.tar.xz \
    && tar -xf blender-2.93.9-linux-x64.tar.xz \
    && mv blender-2.93.9-linux-x64 /usr/local/blender \
    && rm blender-2.93.9-linux-x64.tar.xz \
    && rm -rf /usr/local/blender/2.93/scripts/addons/* \
    && rm -rf /usr/local/blender/2.93/datafiles/locale/* \
    && rm -rf /usr/local/blender/2.93/scripts/modules/bl_i18n_utils

# Create non-root user
RUN useradd -m -s /bin/bash blenderuser && \
    mkdir -p /tmp/blender-config && \
    chmod -R 777 /tmp && \
    chown -R blenderuser:blenderuser /tmp && \
    chown -R blenderuser:blenderuser /usr/local/blender

# Set Blender environment variables
ENV PATH="/usr/local/blender:${PATH}" \
    BLENDER_USER_CONFIG=/tmp/blender-config \
    BLENDER_USER_SCRIPTS=/usr/local/blender/2.93/scripts \
    BLENDER_SYSTEM_SCRIPTS=/usr/local/blender/2.93/scripts \
    XDG_CONFIG_HOME=/tmp/blender-config

# Switch to non-root user
USER blenderuser
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/blenderuser/.local
ENV PATH="/home/blenderuser/.local/bin:${PATH}"

# Copy application files
COPY --chown=blenderuser:blenderuser . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app