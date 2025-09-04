#!/usr/bin/env python3
"""
Transform seed1.csv to the format expected by the company seeder
"""

import csv
import re
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_domain_from_name(company_name):
    """
    Attempt to extract or generate a domain from company name
    This is a fallback since the CSV doesn't have domains
    """
    if not company_name:
        return ""
    
    # Clean company name for domain generation
    name = company_name.lower()
    
    # Remove common suffixes
    name = re.sub(r'\s*(inc\.?|llc\.?|corporation|corp\.?|ltd\.?|limited)\s*$', '', name, flags=re.IGNORECASE)
    
    # Remove special characters and spaces
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '', name)
    
    # Common domain patterns
    if name:
        return f"{name}.com"
    
    return ""

def clean_industry(industry_str):
    """Clean and standardize industry field"""
    if not industry_str or industry_str == 'N/A':
        return "Unknown"
    
    # Remove numbers like "+2", "+3" etc.
    industry = re.sub(r',?\s*\+\d+', '', industry_str)
    
    # Take first industry if multiple
    industry = industry.split(',')[0].strip()
    
    return industry

def clean_location(location_str):
    """Clean location field"""
    if not location_str or location_str == 'N/A':
        return ""
    
    # Remove quotes
    location = location_str.strip('"')
    
    return location

def transform_csv(input_file, output_file):
    """Transform seed1.csv to expected format"""
    
    transformed_companies = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            
            for row_num, row in enumerate(reader, 2):  # Start from 2 since header is row 1
                try:
                    # Skip empty rows
                    if not row.get('Name') or row.get('Name').strip() == '':
                        logger.warning(f"Skipping empty row {row_num}")
                        continue
                    
                    company_name = row['Name'].strip()
                    
                    # Extract employee count
                    employee_count = 0
                    if row.get('Number of Employees'):
                        try:
                            employee_count = int(row['Number of Employees'])
                        except ValueError:
                            logger.warning(f"Invalid employee count for {company_name}: {row.get('Number of Employees')}")
                            employee_count = 75  # Default fallback
                    
                    # Skip if not in target range (50-100 employees)
                    if not (50 <= employee_count <= 100):
                        logger.info(f"Skipping {company_name} - employee count {employee_count} outside range")
                        continue
                    
                    # No domain available in source CSV - leave empty
                    domain = ''  # Will be set to NULL in database
                    
                    # Clean other fields
                    industry = clean_industry(row.get('Industries', ''))
                    location = clean_location(row.get('Location', ''))
                    
                    # Create transformed row
                    transformed_row = {
                        'name': company_name,
                        'domain': domain,
                        'industry': industry,
                        'employee_count': employee_count,
                        'location': location,
                        'founded_year': '',  # Not available in source
                        'linkedin_url': '',  # Not available in source
                        'source': 'manual_import'
                    }
                    
                    transformed_companies.append(transformed_row)
                    logger.info(f"Transformed: {company_name} -> {domain} ({employee_count} employees)")
                    
                except Exception as e:
                    logger.error(f"Error processing row {row_num}: {e}")
                    continue
        
        # Write transformed data
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            if transformed_companies:
                fieldnames = ['name', 'domain', 'industry', 'employee_count', 'location', 'founded_year', 'linkedin_url', 'source']
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(transformed_companies)
        
        logger.info(f"✅ Successfully transformed {len(transformed_companies)} companies")
        logger.info(f"Output saved to: {output_file}")
        
        return transformed_companies
        
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_file}")
        return []
    except Exception as e:
        logger.error(f"Error transforming CSV: {e}")
        return []

def preview_transformation(companies, limit=5):
    """Preview transformed companies"""
    logger.info(f"\n📋 Preview of transformed companies (showing {min(limit, len(companies))}):")
    
    for i, company in enumerate(companies[:limit]):
        logger.info(f"{i+1}. {company['name']}")
        logger.info(f"   Domain: {company['domain']}")
        logger.info(f"   Industry: {company['industry']}")
        logger.info(f"   Employees: {company['employee_count']}")
        logger.info(f"   Location: {company['location']}")
        logger.info("")

def main():
    input_file = "data/seed1.csv"
    output_file = "data/company_import.csv"
    
    logger.info("🔄 Transforming seed1.csv for company seeder...")
    
    # Transform the CSV
    companies = transform_csv(input_file, output_file)
    
    if companies:
        # Show preview
        preview_transformation(companies)
        
        # Test with existing seeder
        logger.info("🧪 Testing with existing company seeder...")
        try:
            from company_seeder import CompanySeeder
            seeder = CompanySeeder()
            
            # Test import
            imported_companies = seeder.seed_from_csv(output_file)
            logger.info(f"✅ Successfully tested import: {len(imported_companies)} companies loaded")
            
            # Show statistics
            employee_counts = [c.employee_count for c in imported_companies]
            logger.info(f"📊 Employee count range: {min(employee_counts)} - {max(employee_counts)}")
            
            industries = [c.industry for c in imported_companies]
            unique_industries = len(set(industries))
            logger.info(f"📊 Unique industries: {unique_industries}")
            
        except Exception as e:
            logger.error(f"❌ Test import failed: {e}")
    
    else:
        logger.error("❌ No companies were successfully transformed")

if __name__ == "__main__":
    main()