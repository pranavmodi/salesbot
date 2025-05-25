# CSV to PostgreSQL Migration Guide

This guide documents the migration from CSV-based data storage to PostgreSQL database for the sales automation system.

## Overview

The sales automation system has been updated to use PostgreSQL database exclusively for contact data instead of CSV files. This provides better performance, data integrity, and scalability.

## What Changed

### Files Updated
- `app/models/contact.py` - Now loads contacts from PostgreSQL
- `send_emails.py` - Now reads contacts from PostgreSQL 
- `email_ui.py` - Now loads leads from PostgreSQL
- `app/config.py` - Removed CSV_FILE_PATH configuration

### CSV Files Found
The following CSV files were identified in your project:
- `email_history.csv` (80KB, 96 lines)
- `dummy_leads.csv` (224B, 4 lines) 
- `test_leads.csv` (112B, 2 lines)
- `contacts/apollo-contacts-export.csv` (37KB, 21 lines)
- `contacts/leads_with_messages.csv` (55KB, 98 lines)
- `Find-People-Table-(21-April-2025)-Default-view-export-1745236524011.csv` (25KB, 97 lines)

## Migration Steps

### 1. Ensure Database is Set Up
Make sure your PostgreSQL database is running and the `DATABASE_URL` environment variable is configured:

```bash
# Example DATABASE_URL format
DATABASE_URL=postgresql://username:password@localhost:5432/salesbot
```

### 2. Run Database Migrations
Ensure all Alembic migrations are applied:

```bash
alembic upgrade head
```

### 3. Migrate CSV Data
Run the migration script to import all CSV data into PostgreSQL:

```bash
python migrate_csv_to_postgres.py
```

This script will:
- Find all CSV files in the project
- Process them using the existing data ingestion system
- Import contacts into the PostgreSQL `contacts` table
- Provide migration statistics
- Optionally backup CSV files

### 4. Verify Migration
After migration, verify the data:

```bash
# Check if contacts were imported
python -c "
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM contacts'))
    print(f'Total contacts: {result.scalar()}')
"
```

### 5. Test the Application
Test that the application works correctly with PostgreSQL:

```bash
# Test email UI
python email_ui.py

# Test email sending
python send_emails.py
```

## Database Schema

The PostgreSQL database includes these key tables:

### `contacts` table
- `email` (Primary Key)
- `first_name`, `last_name`, `full_name`
- `job_title`, `company_name`, `company_domain`
- `linkedin_profile`, `location`, `phone`
- `linkedin_message`
- `created_at`, `updated_at`
- `source_files` (JSONB) - tracks source CSV files
- `all_data` (JSONB) - stores original CSV row data

### `email_history` table
- `id`, `date`, `to`, `subject`, `body`, `status`

### `file_metadata` table
- Tracks CSV file processing metadata

### `column_mappings` table
- Stores column mapping information for data ingestion

## Benefits of PostgreSQL Migration

1. **Performance**: Database queries are much faster than CSV parsing
2. **Data Integrity**: ACID compliance and constraints prevent data corruption
3. **Scalability**: Can handle much larger datasets efficiently
4. **Concurrent Access**: Multiple processes can access data safely
5. **Rich Queries**: Complex filtering, searching, and sorting capabilities
6. **Backup/Recovery**: Built-in database backup and recovery options

## Backward Compatibility

The migration maintains backward compatibility:
- Contact model properties remain the same
- UI templates continue to work unchanged
- Email composer receives the same data format

## Troubleshooting

### Common Issues

1. **DATABASE_URL not configured**
   - Set the `DATABASE_URL` environment variable
   - Check that PostgreSQL is running and accessible

2. **Migration fails**
   - Check CSV file formatting
   - Review migration logs for specific errors
   - Ensure database permissions are correct

3. **No contacts loaded**
   - Verify migration completed successfully
   - Check that contacts table has data
   - Review application logs for database connection errors

### Rollback (if needed)

If you need to rollback to CSV temporarily:
1. Restore CSV files from backup
2. Revert the changed Python files
3. Update configuration to use CSV_FILE_PATH

However, this is not recommended as the PostgreSQL approach is superior.

## Next Steps

1. **Remove CSV Files**: After verifying everything works, you can safely remove CSV files
2. **Add Data Validation**: Consider adding more database constraints
3. **Optimize Queries**: Add indexes for frequently searched fields
4. **Regular Backups**: Set up automated PostgreSQL backups
5. **Monitor Performance**: Track database performance and query optimization

## Data Ingestion

For new CSV files, use the existing data ingestion system:

```bash
# Process new CSV files
python data_ingestion_system.py

# Or run the ingestion script
./run_ingestion.sh
```

The system will automatically:
- Detect CSV column formats
- Map columns to database fields
- Handle duplicates and updates
- Track file processing metadata

## Support

If you encounter issues:
1. Check the application logs
2. Verify database connectivity
3. Review the migration script output
4. Ensure all dependencies are installed

The system is now fully database-driven and should provide better performance and reliability for your sales automation needs. 