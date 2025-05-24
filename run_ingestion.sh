#!/bin/bash

# Sales Bot Data Ingestion Runner Script
# This script activates the virtual environment and runs the data ingestion system

echo "🚀 Starting Sales Bot Data Ingestion System..."
echo "=============================================="

# Activate virtual environment and run ingestion
source salesbot/bin/activate
./salesbot/bin/python data_ingestion_system.py

echo ""
echo "📊 Running Database Statistics..."
echo "=================================="
./salesbot/bin/python database_utils.py

echo ""
echo "✅ Data ingestion complete!" 