#!/usr/bin/env python3
"""
CLI Module

Command line interface for the deep research companies tool.
Handles argument parsing and coordinates the research workflow.
"""

import os
import sys
import logging
import argparse

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .company_researcher import CompanyResearcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('company_research.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the company research script."""
    parser = argparse.ArgumentParser(description='Deep research agent for companies from contacts table')
    parser.add_argument('--max-companies', type=int, help='Maximum number of companies to process')
    parser.add_argument('--company-id', type=int, help='Research a specific company by ID')
    parser.add_argument('--delay', type=int, default=2, help='Delay between API calls in seconds')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without actually doing it')
    parser.add_argument('--no-reports', action='store_true', help='Skip generating strategic reports and markdown files')
    parser.add_argument('--show-reports', action='store_true', help='List all companies with reports in database')
    parser.add_argument('--get-report', type=int, help='Get markdown report for specific company ID from database')
    parser.add_argument('--force-refresh', action='store_true', help='Overwrite existing research (for single company or batch)')
    parser.add_argument('--research-missing', action='store_true', help='Research companies that exist but have no research data')
    parser.add_argument('--show-missing', action='store_true', help='List companies that exist but have no research')
    
    args = parser.parse_args()
    
    try:
        researcher = CompanyResearcher()
        
        # Handle showing reports from database
        if args.show_reports:
            logger.info("Fetching companies with reports from database...")
            companies_with_reports = researcher.db_service.get_companies_with_reports()
            
            if companies_with_reports:
                logger.info(f"Found {len(companies_with_reports)} companies with reports:")
                for company in companies_with_reports:
                    logger.info(f"  ID: {company['id']} | {company['company_name']} | Updated: {company['updated_at']}")
                logger.info("\nUse --get-report <ID> to retrieve a specific report")
            else:
                logger.info("No companies with reports found in database")
            return
        
        # Handle getting specific report from database
        if args.get_report:
            logger.info(f"Fetching report for company ID: {args.get_report}")
            markdown_report = researcher.db_service.get_company_markdown_report(args.get_report)
            
            if markdown_report:
                print("\n" + "="*80)
                print(markdown_report)
                print("="*80)
            else:
                logger.error(f"No report found for company ID: {args.get_report}")
                exit(1)
            return
        
        # Handle showing companies without research
        if args.show_missing:
            logger.info("Fetching companies without research from database...")
            companies_without_research = researcher.db_service.get_companies_without_research()
            
            if companies_without_research:
                logger.info(f"Found {len(companies_without_research)} companies without research:")
                for company in companies_without_research:
                    logger.info(f"  ID: {company['id']} | {company['company_name']} | Created: {company['created_at']}")
                logger.info("\nUse --research-missing to research these companies")
            else:
                logger.info("All existing companies have research data")
            return
        
        # Handle single company research
        if args.company_id:
            logger.info(f"Researching single company with ID: {args.company_id}")
            generate_report = not args.no_reports
            force_refresh = args.force_refresh
            
            success = researcher.research_single_company_by_id(
                args.company_id, 
                generate_report=generate_report,
                force_refresh=force_refresh
            )
            if success:
                logger.info("✅ Single company research completed successfully")
                if generate_report:
                    logger.info("📝 Strategic report generated in deepresearch/reports/ directory")
            else:
                logger.error("❌ Single company research failed")
                exit(1)
            return
        
        # Handle batch processing
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual processing will occur")
            force_refresh = args.force_refresh
            skip_existing = not args.research_missing
            
            preview = researcher.get_dry_run_preview(
                max_companies=args.max_companies,
                skip_existing=skip_existing,
                force_refresh=force_refresh
            )
            
            logger.info(f"Filter mode: {preview['filter_mode']}")
            logger.info(f"Would process {preview['total_companies_to_research']} companies:")
            for i, company in enumerate(preview['companies_preview'], 1):
                logger.info(f"  {i}. {company['company_name']} ({company['contact_count']} contacts)")
            
            if preview['has_more']:
                remaining = preview['total_companies_to_research'] - len(preview['companies_preview'])
                logger.info(f"  ... and {remaining} more")
            
            if not args.no_reports:
                logger.info("Strategic reports would be generated for each company in deepresearch/reports/")
        else:
            generate_reports = not args.no_reports
            force_refresh = args.force_refresh
            skip_existing = not args.research_missing  # If research_missing is True, skip_existing is False
            
            logger.info("Starting deep research agent...")
            if generate_reports:
                logger.info("Strategic reports will be generated in deepresearch/reports/ directory")
            else:
                logger.info("Strategic report generation disabled")
            
            if force_refresh:
                logger.info("🔄 Force refresh mode: Will overwrite existing research")
            elif args.research_missing:
                logger.info("📝 Research missing mode: Will research companies without research data")
            else:
                logger.info("⏭️ Default mode: Will skip companies that already have research")
                
            researcher.process_companies(
                max_companies=args.max_companies,
                delay_seconds=args.delay,
                generate_reports=generate_reports,
                skip_existing=skip_existing,
                force_refresh=force_refresh
            )
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        raise

if __name__ == "__main__":
    main() 