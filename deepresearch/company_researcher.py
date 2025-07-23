#!/usr/bin/env python3
"""
Company Researcher

Main orchestrator for company research operations that coordinates:
- Database operations via DatabaseService
- AI research via AIResearchService  
- Report generation via ReportGenerator
"""

import logging
import time
from typing import Optional

from .database_service import DatabaseService
from .ai_research_service import AIResearchService
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class CompanyResearcher:
    """Main orchestrator for company research operations."""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.ai_service = AIResearchService()
        self.report_generator = ReportGenerator()
        logger.info("CompanyResearcher initialized with all services")

    def research_single_company_by_id(self, company_id: int, generate_report: bool = True, force_refresh: bool = False) -> bool:
        """Research a single company by its ID and optionally generate strategic report."""
        logger.info(f"Starting research for company ID: {company_id}")
        
        # Get company details
        company = self.db_service.get_company_by_id(company_id)
        if not company:
            logger.error(f"Company with ID {company_id} not found")
            return False
        
        company_name = company['company_name']
        website_url = company['website_url'] or ''
        existing_research = company.get('company_research')
        
        # Check if research already exists
        if existing_research and not force_refresh:
            logger.info(f"⚠️ Company {company_name} already has research. Use --force-refresh to overwrite.")
            logger.info(f"📊 Existing research length: {len(existing_research)} characters")
            if generate_report and company.get('markdown_report'):
                logger.info(f"📝 Markdown report already exists")
            return True
        
        if existing_research and force_refresh:
            logger.info(f"🔄 Force refresh enabled - overwriting existing research for: {company_name}")
        
        # Extract domain from website URL for research
        company_domain = ''
        if website_url:
            if website_url.startswith(('http://', 'https://')):
                company_domain = website_url.replace('https://', '').replace('http://', '').split('/')[0]
            else:
                company_domain = website_url
        
        logger.info(f"Researching company: {company_name}")
        
        # Research the company
        research = self.ai_service.research_company(company_name, company_domain)
        
        if research:
            # Update the existing company record
            if self.db_service.update_company_research(company_id, research):
                logger.info(f"✅ Successfully researched and updated: {company_name}")
                
                # Generate strategic recommendations and markdown report if requested
                if generate_report:
                    logger.info(f"Generating strategic analysis for: {company_name}")
                    strategic_analysis = self.ai_service.generate_strategic_recommendations(company_name, research)
                    
                    # Generate strategic imperatives and agent recommendations
                    logger.info(f"Generating strategic imperatives and agent recommendations for: {company_name}")
                    strategic_imperatives, agent_recommendations = self.ai_service.generate_strategic_imperatives_and_agent_recommendations(company_name, research)
                    
                    if strategic_analysis:
                        # Generate markdown report content
                        markdown_content = self.report_generator.generate_markdown_report(company_name, research, strategic_analysis)
                        
                        # Update database with markdown report and new fields
                        if self.db_service.update_company_research(company_id, research, markdown_content, strategic_imperatives, agent_recommendations):
                            logger.info(f"📊 Successfully updated database with markdown report and strategic data for: {company_name}")
                        else:
                            logger.warning(f"⚠️ Failed to update database with markdown report for: {company_name}")
                        
                        # Note: Markdown report is now only stored in database, not as disk file
                    else:
                        logger.warning(f"⚠️ Failed to generate strategic analysis for: {company_name}")
                        # Still save strategic imperatives and agent recommendations even if strategic analysis failed
                        if strategic_imperatives or agent_recommendations:
                            self.db_service.update_company_research(company_id, research, None, strategic_imperatives, agent_recommendations)
                
                return True
            else:
                logger.error(f"❌ Failed to update research for: {company_name}")
                return False
        else:
            logger.error(f"❌ Failed to research: {company_name}")
            return False

    def process_companies(self, max_companies: Optional[int] = None, delay_seconds: int = 2, generate_reports: bool = True, 
                         skip_existing: bool = True, force_refresh: bool = False):
        """Main processing function to research and save companies."""
        logger.info("Starting company research process...")
        
        # Get unique companies from contacts
        contact_companies = self.db_service.get_unique_companies_from_contacts()
        if not contact_companies:
            logger.warning("No companies found in contacts table")
            return
        
        # Determine filtering strategy based on options
        if force_refresh:
            # Force refresh: research all companies, even those with existing research
            existing_companies = set()  # Empty set means no filtering
            logger.info("🔄 Force refresh mode: Will research all companies (overwriting existing)")
        elif skip_existing:
            # Skip companies that already have research (default behavior)
            existing_companies = self.db_service.get_companies_with_research()
            logger.info("⏭️ Skip existing mode: Will skip companies that already have research")
        else:
            # Skip only companies that exist in database but have no research
            existing_companies = self.db_service.get_existing_companies()
            logger.info("📝 Research missing mode: Will research companies without research data")
        
        # Filter companies based on chosen strategy
        companies_to_research = []
        for company in contact_companies:
            if company['company_name'].lower() not in existing_companies:
                companies_to_research.append(company)
        
        filter_desc = "force refresh all" if force_refresh else ("skip with research" if skip_existing else "skip existing records")
        logger.info(f"Found {len(companies_to_research)} companies to research ({filter_desc})")
        
        if max_companies:
            companies_to_research = companies_to_research[:max_companies]
            logger.info(f"Limited to {max_companies} companies for this run")
        
        # Process each company
        successful_count = 0
        failed_count = 0
        reports_generated = 0
        
        for i, company in enumerate(companies_to_research, 1):
            logger.info(f"Processing {i}/{len(companies_to_research)}: {company['company_name']}")
            
            # Construct website URL
            website_url = ""
            if company['company_domain']:
                if not company['company_domain'].startswith(('http://', 'https://')):
                    website_url = f"https://{company['company_domain']}"
                else:
                    website_url = company['company_domain']
            
            # Research the company
            research = self.ai_service.research_company(
                company['company_name'], 
                company['company_domain']
            )
            
            if research:
                # Generate strategic recommendations first if requested
                strategic_analysis = None
                markdown_content = None
                
                strategic_imperatives = None
                agent_recommendations = None
                
                if generate_reports:
                    logger.info(f"Generating strategic analysis for: {company['company_name']}")
                    strategic_analysis = self.ai_service.generate_strategic_recommendations(company['company_name'], research)
                    
                    # Generate strategic imperatives and agent recommendations
                    logger.info(f"Generating strategic imperatives and agent recommendations for: {company['company_name']}")
                    strategic_imperatives, agent_recommendations = self.ai_service.generate_strategic_imperatives_and_agent_recommendations(company['company_name'], research)
                    
                    if strategic_analysis:
                        # Generate markdown report content
                        markdown_content = self.report_generator.generate_markdown_report(company['company_name'], research, strategic_analysis)
                    else:
                        logger.warning(f"⚠️ Failed to generate strategic analysis for: {company['company_name']}")
                
                # Save to database (with or without markdown report)
                save_success = False
                if force_refresh and company['company_name'].lower() in self.db_service.get_existing_companies():
                    # Company exists, we need to update it
                    # First find the company ID
                    all_existing = self.db_service.get_existing_companies()
                    if company['company_name'].lower() in all_existing:
                        # Get company by name to find ID (we'll need to add this method)
                        save_success = self.db_service.update_existing_company_by_name(
                            company['company_name'], website_url, research, markdown_content, strategic_imperatives, agent_recommendations
                        )
                else:
                    # Normal insert for new company
                    save_success = self.db_service.save_company_research(
                        company['company_name'], website_url, research, markdown_content, strategic_imperatives, agent_recommendations
                    )
                
                if save_success:
                    successful_count += 1
                    logger.info(f"✅ Successfully processed: {company['company_name']}")
                    
                    # Note: Markdown report is now only stored in database, not as disk file
                    if generate_reports and strategic_analysis:
                        reports_generated += 1
                        logger.info(f"📊 Successfully stored markdown report in database for: {company['company_name']}")
                        
                        # Additional delay for report generation to avoid rate limiting
                        if i < len(companies_to_research):
                            logger.debug(f"Waiting additional {delay_seconds} seconds after report generation...")
                            time.sleep(delay_seconds)
                else:
                    failed_count += 1
                    logger.error(f"❌ Failed to save: {company['company_name']}")
            else:
                failed_count += 1
                logger.error(f"❌ Failed to research: {company['company_name']}")
            
            # Add delay between API calls to avoid rate limiting
            if i < len(companies_to_research):
                logger.debug(f"Waiting {delay_seconds} seconds before next request...")
                time.sleep(delay_seconds)
        
        # Final summary
        summary = f"""
Company Research Complete!
========================
Total companies processed: {len(companies_to_research)}
Successfully researched: {successful_count}
Failed: {failed_count}
Success rate: {(successful_count/len(companies_to_research)*100):.1f}%"""
        
        if generate_reports:
            summary += f"""
Strategic reports stored in database: {reports_generated}
Report success rate: {(reports_generated/successful_count*100):.1f}% (of successful research)"""
        
        logger.info(summary)

    def get_dry_run_preview(self, max_companies: Optional[int] = None, skip_existing: bool = True, force_refresh: bool = False) -> dict:
        """Get a preview of what would be processed in a dry run."""
        contact_companies = self.db_service.get_unique_companies_from_contacts()
        
        # Use same filtering logic as process_companies
        if force_refresh:
            existing_companies = set()
            filter_mode = "force refresh all"
        elif skip_existing:
            existing_companies = self.db_service.get_companies_with_research()
            filter_mode = "skip with research"
        else:
            existing_companies = self.db_service.get_existing_companies()
            filter_mode = "skip existing records"
        
        companies_to_research = [
            company for company in contact_companies 
            if company['company_name'].lower() not in existing_companies
        ]
        
        if max_companies:
            companies_to_research = companies_to_research[:max_companies]
        
        return {
            'total_companies_to_research': len(companies_to_research),
            'companies_preview': companies_to_research[:10],  # Show first 10
            'has_more': len(companies_to_research) > 10,
            'filter_mode': filter_mode
        } 