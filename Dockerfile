# Dockerfile for LedgerScope

# Stage 1: Build the Next.js web application
FROM node:18-alpine AS web-builder
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Build the Python environment and serve
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy Python package files
COPY pyproject.toml ./
COPY ledgerscope/ ./ledgerscope/
COPY tests/ ./tests/
COPY README.md ./

# Install LedgerScope from source
RUN pip install --no-cache-dir .

# Copy Next.js build output into a static directory we can serve, if we were sharing a port.
# However, Next.js 'next start' runs its own node server, and FastAPI runs its own python server.
# To serve both in one container easily, we'll install Node.js in the python base image,
# or we just use a small bash script to start both.
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy web files
COPY --from=web-builder /app/web /app/web

# Create a sample fake dataset and ingest it so users have data immediately
COPY tests/fixtures/zerodha_sample.csv /app/sample.csv
# We'll write the script that ingests the sample on start, and runs the servers
RUN echo '#!/bin/bash\n\
# Initialize the DB if it does not exist\n\
if [ ! -f ~/.ledgerscope/ledgerscope.duckdb ]; then\n\
    echo "Ingesting sample dataset..."\n\
    ledgerscope ingest zerodha /app/sample.csv\n\
fi\n\
echo "Starting FastAPI server..."\n\
uvicorn ledgerscope.server:app --host 0.0.0.0 --port 8000 &\n\
echo "Starting Next.js dashboard..."\n\
cd /app/web && npm start -- -p 3000\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000
EXPOSE 3000

CMD ["/app/start.sh"]
