FROM python:3.9-slim

RUN apt-get update && apt-get install -y --no-install-recommends blender \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash blenderuser && \
    mkdir -p /tmp && \
    chmod 777 /tmp && \
    chown -R blenderuser:blenderuser /tmp

USER blenderuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
ENV PATH="/home/blenderuser/.local/bin:${PATH}"

COPY . .
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
