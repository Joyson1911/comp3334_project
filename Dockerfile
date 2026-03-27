# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create output directories
RUN mkdir -p /run/Clients/ /run/Server/ && \
    chown -R appuser:appuser /run

USER appuser

# We will use volumes to mount your code, so we don't COPY source here
WORKDIR /run

# Default command will be overridden by compose.yaml
CMD ["python"]