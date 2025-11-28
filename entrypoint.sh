#!/bin/bash

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Create necessary directories (in case they don't exist)
mkdir -p /app/data /app/instance /app/app/static/uploads

# Initialize database
echo "Initializing database..."
python -c "from app import create_app; app = create_app(); app.app_context().push(); from app import db; db.create_all()"

# Start the application
echo "Starting Flask application..."
exec python main.py
