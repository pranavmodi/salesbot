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

# Show actual database schema for debugging
echo "🔍 Verifying database schema..."
python3 -c "
import os
from sqlalchemy import create_engine, text, inspect
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    inspector = inspect(engine)
    if 'campaigns' in inspector.get_table_names():
        columns = inspector.get_columns('campaigns')
        print('✅ Campaigns columns:', [col['name'] for col in columns])
    else:
        print('❌ Campaigns table does not exist')
        
    if 'companies' in inspector.get_table_names():
        columns = inspector.get_columns('companies')
        col_names = [col['name'] for col in columns]
        print('✅ Companies columns:', col_names)
        
        # Check for critical columns
        required_cols = ['openai_response_id', 'tenant_id', 'llm_research_step_status']
        missing_cols = [col for col in required_cols if col not in col_names]
        if missing_cols:
            print(f'❌ MISSING CRITICAL COLUMNS: {missing_cols}')
            exit(1)
        else:
            print('✅ All critical columns present')
    else:
        print('❌ Companies table does not exist')
        exit(1)
"

echo "✅ Database migrations completed"

# Start the web server with proper Python path
echo "🌐 Starting web server..."
exec env PYTHONPATH="/app:$PYTHONPATH" gunicorn --bind 0.0.0.0:$PORT run:app --timeout 120 --workers 2