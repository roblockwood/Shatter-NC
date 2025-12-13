FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make startup scripts executable
RUN chmod +x /app/scripts/*.sh

# Create non-root user
RUN useradd -m -u 1000 shatter && chown -R shatter:shatter /app

# Development stage
FROM base AS development
USER shatter
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
USER shatter
EXPOSE 8000

# Use startup script that runs migrations first
CMD ["/app/scripts/start.sh"]
