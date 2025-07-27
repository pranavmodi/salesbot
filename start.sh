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

# Set Python path for proper imports
export PYTHONPATH="/app:$PYTHONPATH"

# Run database migrations
echo "🗄️ Running database migrations..."

# Check current revision before migration
echo "📍 Current alembic revision:"
alembic current

# Run the migration
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Database migration failed"
    exit 1
fi

# Check revision after migration
echo "📍 Alembic revision after migration:"
alembic current

echo "✅ Database migrations completed"

# Start the web server with proper Python path
echo "🌐 Starting web server..."
exec env PYTHONPATH="/app:$PYTHONPATH" gunicorn --bind 0.0.0.0:$PORT run:app --timeout 120 --workers 2