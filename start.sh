#!/bin/bash

# Railway startup script with error handling

echo "🚂 Starting Railway deployment..."

# Check if DATABASE_URL is available
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    echo "Please add a PostgreSQL database service to your Railway project"
    exit 1
fi

echo "✅ DATABASE_URL detected"

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Database migration failed"
    exit 1
fi

echo "✅ Database migrations completed"

# Start the web server
echo "🌐 Starting web server..."
exec gunicorn --bind 0.0.0.0:$PORT run:app --timeout 120 --workers 2