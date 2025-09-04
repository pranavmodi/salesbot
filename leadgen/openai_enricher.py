#!/usr/bin/env python3
"""
OpenAI-powered Company Data Enrichment

Uses OpenAI's web search capabilities to find and enrich company information
including domains, industry details, and basic company information.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, List
from .database import get_database_manager
from app.models.leadgen_models import LeadgenCompany as Company
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Structured output schema for OpenAI
class CompanyEnrichmentData(BaseModel):
    company_name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    employee_count: Optional[int] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    linkedin_url: Optional[str] = None
    key_products: Optional[List[str]] = None
    funding_status: Optional[str] = None
    confidence_score: Optional[float] = None

class OpenAICompanyEnricher:
    """Company data enrichment using OpenAI web search"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.db_manager = get_database_manager()
    
    def enrich_company_data(self, company_name: str, existing_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enrich company data using OpenAI web search
        
        Args:
            company_name: Name of the company to enrich
            existing_info: Existing company information (optional)
            
        Returns:
            Dict containing enriched company information
        """
        try:
            # Create search query
            search_query = f"company information for {company_name}"
            if existing_info and existing_info.get('location'):
                search_query += f" located in {existing_info['location']}"
            
            # Create enrichment prompt
            enrichment_prompt = self._create_enrichment_prompt(company_name, existing_info)
            
            logger.info(f"Enriching company data for: {company_name}")
            
            # Call OpenAI API with structured outputs
            response = self.client.beta.chat.completions.parse(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a company research assistant. Search the web for accurate, up-to-date company information. Always provide factual data and set fields to null when information is not available or uncertain."
                    },
                    {
                        "role": "user", 
                        "content": enrichment_prompt
                    }
                ],
                response_format=CompanyEnrichmentData
                # Note: structured outputs only support default temperature (1.0)
            )
            
            # Parse the structured response
            if response.choices[0].message.parsed:
                enriched_data = response.choices[0].message.parsed.model_dump()
            else:
                # Fallback if parsing fails
                logger.warning(f"Structured parsing failed for {company_name}, using fallback")
                enriched_data = {"error": "Failed to parse structured response"}
            
            # Add metadata
            enriched_data['enrichment_date'] = datetime.now().isoformat()
            enriched_data['enrichment_source'] = 'openai_web_search'
            enriched_data['original_query'] = search_query
            
            logger.info(f"Successfully enriched data for {company_name}")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to enrich company {company_name}: {e}")
            return {
                'error': str(e),
                'enrichment_date': datetime.now().isoformat(),
                'enrichment_source': 'openai_web_search_failed'
            }
    
    def _create_enrichment_prompt(self, company_name: str, existing_info: Dict[str, Any] = None) -> str:
        """Create a detailed prompt for company enrichment"""
        
        prompt = f"""
Please search for and provide accurate information about the company "{company_name}".

I need the following information in JSON format:
{{
    "company_name": "Official company name",
    "domain": "Primary website domain (e.g., company.com)",
    "industry": "Primary industry/sector", 
    "description": "Brief company description (1-2 sentences)",
    "employee_count": "Approximate number of employees (integer or null if unknown)",
    "founded_year": "Year company was founded (integer or null if unknown)",
    "headquarters": "Location of headquarters (City, State/Country)",
    "linkedin_url": "LinkedIn company page URL if available",
    "key_products": ["List of main products or services"],
    "funding_status": "Funding status (e.g., 'Private', 'Public', 'Acquired', etc.)",
    "confidence_score": 0.95
}}

Current information I have:
"""
        
        if existing_info:
            prompt += f"- Industry: {existing_info.get('industry', 'Unknown')}\n"
            prompt += f"- Employee count: {existing_info.get('employee_count', 'Unknown')}\n"
            prompt += f"- Location: {existing_info.get('location', 'Unknown')}\n"
        else:
            prompt += "- No existing information available\n"
        
        prompt += """
Please verify and enhance this information. If you cannot find reliable information for a field, set it to null.
Only provide information you are confident about. Return ONLY the JSON object, no additional text.
"""
        
        return prompt
    
    def _parse_text_response(self, text_response: str) -> Dict[str, Any]:
        """Parse non-JSON text response into structured data"""
        
        # Basic text parsing fallback
        result = {
            'company_name': None,
            'domain': None,
            'industry': None,
            'description': None,
            'employee_count': None,
            'founded_year': None,
            'headquarters': None,
            'linkedin_url': None,
            'key_products': [],
            'funding_status': None,
            'confidence_score': 0.5,
            'raw_response': text_response
        }
        
        # Simple regex patterns to extract information
        import re
        
        # Extract domain
        domain_match = re.search(r'(?:website|domain|url)[:\s]+([a-zA-Z0-9.-]+\.com)', text_response, re.IGNORECASE)
        if domain_match:
            result['domain'] = domain_match.group(1).lower()
        
        # Extract employee count
        employee_match = re.search(r'(?:employees|staff)[:\s]+(\d+)', text_response, re.IGNORECASE)
        if employee_match:
            result['employee_count'] = int(employee_match.group(1))
        
        # Extract year
        year_match = re.search(r'(?:founded|established)[:\s]+(\d{4})', text_response, re.IGNORECASE)
        if year_match:
            result['founded_year'] = int(year_match.group(1))
        
        return result
    
    def enrich_company_by_id(self, company_id: int) -> Dict[str, Any]:
        """Enrich a specific company by database ID"""
        
        try:
            logger.info(f"Starting enrichment for company ID {company_id}")
            
            with self.db_manager.session_scope() as session:
                company = session.query(Company).filter(Company.id == company_id).first()
                
                if not company:
                    error_msg = f"Company with ID {company_id} not found"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                logger.info(f"Found company: {company.name} (ID: {company_id})")
                
                # Prepare existing info
                existing_info = {
                    'industry': company.industry,
                    'employee_count': company.employee_count,
                    'location': company.location,
                    'domain': company.domain,
                    'founded_year': company.founded_year
                }
                logger.info(f"Existing info for {company.name}: {existing_info}")
                
                # Get enriched data
                logger.info(f"Calling enrich_company_data for {company.name}")
                enriched_data = self.enrich_company_data(company.name, existing_info)
                logger.info(f"Enrichment result for {company.name}: {enriched_data}")
                
                # Update company with enriched data if successful
                if 'error' not in enriched_data:
                    logger.info(f"Updating company {company.name} with enriched data")
                    self._update_company_with_enriched_data(company, enriched_data)
                    session.commit()
                    logger.info(f"Successfully updated company {company.name} with enriched data")
                else:
                    logger.error(f"Enrichment failed for {company.name}: {enriched_data.get('error')}")
                
                return enriched_data
                
        except Exception as e:
            logger.error(f"Exception in enrich_company_by_id for company {company_id}: {e}", exc_info=True)
            return {
                'error': str(e),
                'enrichment_date': datetime.now().isoformat(),
                'enrichment_source': 'openai_web_search_failed'
            }
    
    def _update_company_with_enriched_data(self, company: Company, enriched_data: Dict[str, Any]):
        """Update company object with enriched data"""
        
        # Update domain if not present and found
        if not company.domain and enriched_data.get('domain'):
            company.domain = enriched_data['domain']
        
        # Update industry if more specific
        if enriched_data.get('industry') and (not company.industry or company.industry == 'Unknown'):
            company.industry = enriched_data['industry']
        
        # Update employee count if not present
        if not company.employee_count and enriched_data.get('employee_count'):
            try:
                company.employee_count = int(enriched_data['employee_count'])
            except (ValueError, TypeError):
                pass
        
        # Update founded year if not present
        if not company.founded_year and enriched_data.get('founded_year'):
            try:
                company.founded_year = int(enriched_data['founded_year'])
            except (ValueError, TypeError):
                pass
        
        # Update LinkedIn URL if not present
        if not company.linkedin_url and enriched_data.get('linkedin_url'):
            company.linkedin_url = enriched_data['linkedin_url']
        
        # Update location if more specific
        if enriched_data.get('headquarters') and (not company.location or len(enriched_data['headquarters']) > len(company.location or '')):
            company.location = enriched_data['headquarters']
        
        # Store full enrichment data in technology_stack as metadata (temporary solution)
        if not company.technology_stack:
            company.technology_stack = []
        
        # Add enrichment metadata
        enrichment_metadata = {
            'enriched_at': enriched_data.get('enrichment_date'),
            'enriched_by': 'openai_web_search',
            'confidence_score': enriched_data.get('confidence_score', 0.5),
            'key_products': enriched_data.get('key_products', []),
            'description': enriched_data.get('description'),
            'funding_status': enriched_data.get('funding_status')
        }
        
        # Add to technology stack for now (we can create a separate enrichment table later)
        if isinstance(company.technology_stack, list):
            company.technology_stack.append(f"enriched:{json.dumps(enrichment_metadata)}")
    
    def enrich_companies_batch(self, company_ids: List[int], max_concurrent: int = 3) -> Dict[int, Dict[str, Any]]:
        """Enrich multiple companies in batch with rate limiting"""
        
        results = {}
        
        async def enrich_single(company_id: int):
            try:
                result = self.enrich_company_by_id(company_id)
                results[company_id] = result
                # Add delay to respect rate limits
                await asyncio.sleep(2)  # 2 second delay between requests
            except Exception as e:
                results[company_id] = {'error': str(e)}
        
        async def run_batch():
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def limited_enrich(company_id):
                async with semaphore:
                    await enrich_single(company_id)
            
            tasks = [limited_enrich(company_id) for company_id in company_ids]
            await asyncio.gather(*tasks)
        
        # Run the batch enrichment
        asyncio.run(run_batch())
        
        return results

def main():
    """CLI for testing company enrichment"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich company data using OpenAI')
    parser.add_argument('--company-id', type=int, help='Enrich specific company by ID')
    parser.add_argument('--company-name', type=str, help='Enrich company by name (direct search)')
    parser.add_argument('--batch', type=str, help='Comma-separated company IDs to enrich in batch')
    parser.add_argument('--sample', action='store_true', help='Enrich first 5 companies without domains')
    
    args = parser.parse_args()
    
    enricher = OpenAICompanyEnricher()
    
    if args.company_id:
        # Enrich specific company
        result = enricher.enrich_company_by_id(args.company_id)
        print(json.dumps(result, indent=2))
    
    elif args.company_name:
        # Direct company search
        result = enricher.enrich_company_data(args.company_name)
        print(json.dumps(result, indent=2))
    
    elif args.batch:
        # Batch enrichment
        company_ids = [int(id.strip()) for id in args.batch.split(',')]
        results = enricher.enrich_companies_batch(company_ids)
        print(json.dumps(results, indent=2))
    
    elif args.sample:
        # Enrich sample companies
        db = get_database_manager()
        with db.session_scope() as session:
            # Get first 5 companies without domains
            companies = session.query(Company).filter(
                Company.domain.is_(None)
            ).limit(5).all()
            
            company_ids = [c.id for c in companies]
            print(f"Enriching {len(company_ids)} sample companies: {[c.name for c in companies]}")
            
            results = enricher.enrich_companies_batch(company_ids)
            
            # Show summary
            successful = sum(1 for r in results.values() if 'error' not in r)
            print(f"\n📊 Enrichment Results:")
            print(f"   Successful: {successful}/{len(results)}")
            print(f"   Failed: {len(results) - successful}/{len(results)}")
    
    else:
        print("Please specify --company-id, --company-name, --batch, or --sample")

if __name__ == "__main__":
    main()