# Sales Bot Contact Data Ingestion System

This system provides a robust solution for ingesting contact data from multiple CSV files with different column structures into a unified PostgreSQL database. It's designed specifically for a sales automation chatbot that helps healthcare companies with AI-powered customer support.

## Features

- **Multi-format CSV ingestion**: Handles CSV files with different column structures automatically
- **Email-based deduplication**: Uses email as primary key to prevent duplicates
- **Intelligent column mapping**: Automatically maps different column names to standardized fields
- **Complete data preservation**: Stores all original data in JSONB format alongside standardized fields
- **Source tracking**: Tracks which files each contact came from
- **Flexible querying**: Comprehensive search and filter capabilities
- **Export functionality**: Export filtered data back to CSV
- **PostgreSQL with Alembic**: Professional database management with version-controlled migrations

## Database Schema

### Main Tables

#### `contacts` table
- `email` (PRIMARY KEY): Contact's email address
- `first_name`: Contact's first name
- `last_name`: Contact's last name  
- `full_name`: Complete name
- `job_title`: Job title/position
- `company_name`: Company name
- `company_domain`: Company website domain
- `linkedin_profile`: LinkedIn profile URL
- `location`: Location/address
- `phone`: Phone number
- `linkedin_message`: Personalized LinkedIn message
- `created_at`: Record creation timestamp (with timezone)
- `updated_at`: Last update timestamp (with timezone)
- `source_files`: JSONB array of source files (for tracking)
- `all_data`: JSONB object with all original data

#### `file_metadata` table
- Tracks processing metadata for each CSV file
- Records row counts, success rates, and column mappings
- Uses JSONB for flexible column mapping storage

#### `column_mappings` table
- Historical record of column mapping decisions
- Useful for improving future automatic mappings

## Quick Start

### 1. Prerequisites

- PostgreSQL database running
- Virtual environment set up
- `DATABASE_URL` environment variable configured

### 2. Database Setup

```bash
# Run migrations to create tables
alembic upgrade head
```

### 3. Install Dependencies

```bash
source salesbot/bin/activate
pip install -r requirements.txt
```

### 4. Run Data Ingestion

```bash
# Easy way - use the provided script
./run_ingestion.sh

# Or manually
source salesbot/bin/activate
./salesbot/bin/python data_ingestion_system.py
```

This will:
- Process all CSV files in the `contacts/` directory
- Store data in PostgreSQL database
- Show processing statistics
- Display database statistics

## Usage Examples

### Basic Data Ingestion

```python
from data_ingestion_system import ContactDataIngester

# Initialize ingester
ingester = ContactDataIngester()
ingester.connect_db()

# Process all CSV files
ingester.process_all_files()

# Get statistics
stats = ingester.get_statistics()
print(f"Total contacts: {stats['total_contacts']}")

ingester.close()
```

### Database Queries

```python
from database_utils import ContactDatabase

with ContactDatabase() as db:
    # Search for contacts
    results = db.search_contacts("GoHealth")
    
    # Get contacts by company
    company_contacts = db.get_contacts_by_company("Fast Pace Health")
    
    # Export filtered data
    db.export_to_csv("gohealth_contacts.csv", 
                     filters={"company_name": "GoHealth"})
```

## Column Mapping Intelligence

The system automatically maps various column naming conventions to standardized fields:

| Standard Field | Recognized Variations |
|---|---|
| `first_name` | "First Name", "firstname", "fname" |
| `last_name` | "Last Name", "lastname", "surname" |
| `company_name` | "Company", "Company Name", "organization" |
| `job_title` | "Title", "Job Title", "position", "role" |
| `linkedin_profile` | "LinkedIn", "LinkedIn Profile", "Person Linkedin Url" |

## Email Detection

The system intelligently identifies email columns by looking for:
- Columns containing "email", "mail", "e-mail"
- Columns with "work email", "primary email"
- Multiple email columns ("Find Work Email", "Find Work Email (2)", etc.)
- Validates email format and excludes error markers like "❌ No email found"

## Data Sources

Currently configured to handle files from:
- Apollo exports (`apollo-contacts-export.csv`)
- Lead generation tools (`leads_with_messages.csv`)
- Any CSV with contact information

The system is designed to be extensible for additional data sources.

## File Structure

```
salesbot/
├── contacts/                    # CSV files directory
│   ├── apollo-contacts-export.csv
│   └── leads_with_messages.csv
├── alembic/                     # Database migrations
│   └── versions/
│       ├── aba854ab6f1f_create_email_history_table.py
│       └── dcfd9b261ec6_create_contacts_table.py
├── data_ingestion_system.py     # Main ingestion script
├── database_utils.py            # Database utilities and queries
├── requirements.txt             # Python dependencies
├── run_ingestion.sh             # Easy run script
├── alembic.ini                  # Alembic configuration
├── productdescription.txt       # Product description for sales bot
└── README.md                    # This file
```

## Advanced Features

### Duplicate Handling
- Automatic deduplication based on email address (PRIMARY KEY)
- When duplicates are found, data is merged with newer information taking precedence
- Source file tracking maintains history of where data originated
- PostgreSQL UPSERT operations for efficient data management

### Data Preservation
- All original data stored in JSONB format in `all_data` field
- No information is lost during standardization process
- Easy to recover original column names and values
- JSONB allows for efficient querying of nested data

### Incremental Updates
- System handles new CSV files without duplicating existing data
- Updates existing contacts with new information
- Tracks which files contributed to each contact record
- ON CONFLICT handling for smooth re-processing

## Database Management

### Migrations

```bash
# Create new migration
alembic revision -m "description_of_change"

# Run migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Monitoring and Maintenance

#### Check Processing Status
```python
with ContactDatabase() as db:
    stats = db.get_database_stats()
    print(f"Processing success rate: {stats['complete_contacts']}/{stats['total_contacts']}")
```

#### Find Contacts Missing Information
```python
with ContactDatabase() as db:
    missing_titles = db.get_contacts_missing_info('job_title')
    missing_linkedin = db.get_contacts_missing_info('linkedin_profile')
```

#### Export for External Tools
```python
with ContactDatabase() as db:
    # Export all GoHealth contacts
    db.export_to_csv("gohealth_export.csv", 
                     filters={"company_name": "GoHealth"})
    
    # Export contacts with LinkedIn messages
    contacts_with_messages = db.get_contacts_with_linkedin_messages()
```

## Performance Features

- **Database Indexes**: Optimized indexes on company_name, job_title, and name fields
- **JSONB Storage**: Efficient storage and querying of JSON data
- **Connection Pooling**: SQLAlchemy connection management
- **Batch Processing**: Efficient bulk operations
- **Transaction Management**: ACID compliance for data integrity

## Error Handling

The system includes comprehensive error handling:
- Invalid email formats are logged and skipped
- CSV parsing errors are captured per file
- Database connection issues are handled gracefully
- SQLAlchemy exceptions properly caught and logged
- Processing statistics include error counts for monitoring

## Environment Configuration

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:pass@localhost/db`)

Example `.env` file:
```env
DATABASE_URL=postgresql://pranav:postgres@localhost:5432/salesdb
```

## Results Summary

Current ingestion results:
- **Total contacts**: 87
- **Unique companies**: 25
- **Success rate**: 75.7% (87/115 rows processed)
- **Top companies**: GoHealth Urgent Care (21), Fast Pace Health (18), NextCare (11)

## Future Enhancements

- **API Integration**: Direct integration with CRM systems
- **Real-time Processing**: Watch folder for new CSV files
- **Data Validation**: Enhanced validation rules for contact data
- **Machine Learning**: Improved column mapping using ML techniques
- **Web Interface**: Browser-based data management interface
- **Webhook Support**: Real-time notifications for new data

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check `DATABASE_URL` environment variable
2. **No CSV files found**: Ensure CSV files are in the `contacts/` directory
3. **Import errors**: Activate virtual environment with `source salesbot/bin/activate`
4. **Encoding issues**: Ensure CSV files are UTF-8 encoded
5. **Permission errors**: Make sure `run_ingestion.sh` is executable

### Logs

The system provides detailed logging. Check console output for:
- Database connection status
- File processing progress
- Column mapping decisions
- Error details and row numbers
- Final processing statistics

## Support

For issues or questions about the data ingestion system:
1. Check the logs first for specific error messages
2. Verify database connectivity and environment variables
3. Review the database statistics to understand current state
4. Check PostgreSQL logs for database-specific issues 