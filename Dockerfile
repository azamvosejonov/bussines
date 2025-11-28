FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=main.py
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user first
RUN useradd --create-home --shell /bin/bash app

# Create necessary directories and set ownership
RUN mkdir -p /app/data /app/instance /app/app/static/uploads \
    && chown -R app:app /app

# Switch to app user before creating database file
USER app

# Create database file as app user
RUN touch /app/biznes.db && chmod 666 /app/biznes.db

# Make entrypoint executable (switch back to root temporarily)
USER root
RUN chmod +x /app/entrypoint.sh

# Switch back to app user
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]
