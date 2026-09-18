# syntax=docker/dockerfile:1
# Hardened, unprivileged container image for F5 Support Case & QKView Automation (qkviewmgr)

FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create unprivileged application user and data directory
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /home/appuser -m appuser && \
    mkdir -p /data && chown -R appuser:appgroup /data

WORKDIR /app

# Copy lockfile and project definition
COPY requirements.lock pyproject.toml ./
COPY src/ ./src/

# Install dependencies using strict cryptographic SHA-256 hash verification
RUN python -m pip install --upgrade pip && \
    pip install --require-hashes --no-deps -r requirements.lock && \
    pip install --no-deps . && \
    rm -rf /root/.cache

# Set metadata labels
LABEL org.opencontainers.image.title="qkviewmgr" \
      org.opencontainers.image.description="CLI tools for F5 BIG-IP QKView generation, retrieval, and MyF5/iHealth support case integration" \
      org.opencontainers.image.url="https://github.com/SalesAmerSP/f5_support_case_creation_api_tools" \
      org.opencontainers.image.source="https://github.com/SalesAmerSP/f5_support_case_creation_api_tools" \
      org.opencontainers.image.licenses="MIT"

# Switch to unprivileged user and set runtime workspace
USER 10001:10001
WORKDIR /data

# Default volume for QKView downloads and generated case inputs
VOLUME ["/data"]

# Entrypoint executes qkviewmgr CLI dispatcher
ENTRYPOINT ["qkviewmgr"]
CMD ["--help"]
