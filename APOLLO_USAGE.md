# Apollo.io Integration for SalesBot

This script integrates with Apollo.io's API to import high-quality lead data directly into your SalesBot CRM system.

## Setup

1. **Get Apollo API Key**
   - Sign up at [Apollo.io](https://apollo.io)
   - Go to Settings → Integrations → API
   - Generate an API key

2. **Configure Environment**
   ```bash
   # Add to your .env file
   APOLLO_API_KEY=your_apollo_api_key_here
   ```

## Quick Start

### Healthcare Example (Recommended)
```bash
# Import 250 healthcare contacts (5 pages × 50 per page)
./salesbot/bin/python apollo_import.py \
  --industry healthcare \
  --employees 50-200 \
  --location "United States" \
  --verified-emails \
  --pages 5
```

### Technology Companies
```bash
./salesbot/bin/python apollo_import.py \
  --industry technology \
  --employees 200-1000 \
  --seniority management \
  --pages 3
```

### Using Configuration File
```bash
# Create sample config
./salesbot/bin/python apollo_import.py --create-sample-config

# Edit apollo_config_sample.json, then run:
./salesbot/bin/python apollo_import.py --config apollo_config_sample.json
```

## Command Line Options

### Search Filters
- `--industry` - Industry type (healthcare, technology, finance, education, manufacturing, retail, or custom)
- `--employees` - Company size (50-200, 200-1000, 1000+, or custom range)
- `--location` - Geographic location (default: "United States")
- `--titles` - Specific job titles (e.g., "Manager" "Director" "VP")
- `--seniority` - Seniority level (executive, management, individual)
- `--verified-emails` - Only fetch verified email addresses

### Fetch Settings
- `--pages` - Number of pages to fetch (default: 5)
- `--per-page` - Results per page, max 200 (default: 50)
- `--api-key` - Apollo API key (or set APOLLO_API_KEY env var)

### Output Options
- `--csv-only` - Export to CSV only, don't import to SalesBot
- `--csv-filename` - Custom CSV filename
- `--tenant-id` - Specific SalesBot tenant for import

## Industry Mappings

The script includes predefined industry mappings for better targeting:

- **healthcare**: Healthcare, Medical Practice, Hospital & Health Care, Pharmaceuticals, Medical Devices
- **technology**: Information Technology, Software, Computer Software, Internet
- **finance**: Financial Services, Banking, Investment Banking, Insurance
- **education**: Education, Higher Education, E-Learning
- **manufacturing**: Manufacturing, Industrial Manufacturing, Automotive
- **retail**: Retail, E-commerce, Consumer Goods

## Sample Configuration File

```json
{
  "search_params": {
    "industry": "healthcare",
    "employees": "50-200",
    "location": "United States",
    "verified_emails": true,
    "titles": ["Manager", "Director", "VP"],
    "seniority": "management"
  },
  "fetch_settings": {
    "pages": 5,
    "per_page": 50,
    "rate_limit_delay": 1.0
  },
  "output": {
    "csv_filename": "apollo_leads_{timestamp}.csv",
    "import_to_salesbot": true,
    "tenant_id": null
  }
}
```

## Data Fields Imported

For each contact, the script imports:
- **Personal**: First name, last name, email, job title
- **Company**: Company name, website URL
- **Additional**: LinkedIn profile, phone number, location
- **Metadata**: Source (apollo), import timestamp

## API Limits & Best Practices

- **Rate Limiting**: Script automatically adds 1-second delays between requests
- **Credits**: Each verified email consumes credits from your Apollo account
- **Pagination**: Automatically handles pagination up to your specified page limit
- **Error Handling**: Continues processing if individual records fail
- **Deduplication**: Skips contacts that already exist in your database

## Output Files

1. **CSV Export**: Always creates a timestamped CSV file
2. **Log File**: Creates `apollo_import.log` with detailed import progress
3. **Database Import**: Directly imports to SalesBot contacts and companies tables

## Example Workflows

### Large Healthcare Import
```bash
# Import 1000 healthcare decision makers
./salesbot/bin/python apollo_import.py \
  --industry healthcare \
  --employees 100-500 \
  --seniority executive \
  --verified-emails \
  --pages 20 \
  --csv-filename "healthcare_executives_$(date +%Y%m%d).csv"
```

### Multi-Industry Import
```bash
# Create separate configs for different industries
# then import each with specific targeting
./salesbot/bin/python apollo_import.py --config healthcare_config.json
./salesbot/bin/python apollo_import.py --config technology_config.json
./salesbot/bin/python apollo_import.py --config finance_config.json
```

### CSV-Only Mode (For Review)
```bash
# Export to CSV first for manual review
./salesbot/bin/python apollo_import.py \
  --industry technology \
  --employees 50-200 \
  --csv-only \
  --pages 2
```

## Troubleshooting

- **API Key Issues**: Verify your Apollo.io API key is valid and has sufficient credits
- **No Results**: Try broader search criteria or different industry keywords
- **Import Errors**: Check the log file for detailed error messages
- **Rate Limits**: Increase `rate_limit_delay` in config if you hit API limits

## Next Steps

After importing contacts:
1. Review imported data in SalesBot dashboard
2. Run company research on new companies
3. Create email campaigns targeting specific segments
4. Use SalesBot's analytics to track engagement