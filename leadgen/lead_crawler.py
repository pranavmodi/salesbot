#!/usr/bin/env python3
"""
Lead Crawler - Similar Company Discovery Engine

This module discovers similar companies based on seed companies and industry.
It uses various APIs and data sources to find companies with similar characteristics.
"""

import asyncio
import logging
import openai
import json
import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session

from database import get_db_session
from models import Company
from openai_enricher import OpenAICompanyEnricher
from lead_scoring import score_company_by_id, save_lead_score_to_db

logger = logging.getLogger(__name__)

@dataclass
class CrawlingProgress:
    """Progress tracking for crawling operations"""
    task_id: str
    stage: str
    progress: float
    message: str
    companies_discovered: int = 0
    companies_added: int = 0
    companies_enriched: int = 0
    companies_scored: int = 0

@dataclass
class DiscoveredCompany:
    """Discovered company data"""
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    similarity_score: float = 0.0
    discovery_method: str = "unknown"
    source_company: Optional[str] = None

class LeadCrawler:
    """Lead crawler for discovering similar companies"""
    
    def __init__(self, openai_api_key: str, progress_callback=None):
        """Initialize the lead crawler"""
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.enricher = OpenAICompanyEnricher(openai_api_key)
        self.progress_callback = progress_callback
        self.discovered_companies: List[DiscoveredCompany] = []
        self.processed_companies: Set[str] = set()
        
    async def crawl_similar_companies(
        self,
        task_id: str,
        seed_companies: List[str],
        industry: str,
        company_size: str,
        max_companies: int = 50,
        crawl_depth: int = 2,
        enable_enrichment: bool = True,
        enable_scoring: bool = True,
        skip_existing: bool = True
    ) -> Dict:
        """
        Main crawling method to discover similar companies
        """
        try:
            await self._update_progress(task_id, "initializing", 0, "Initializing crawler...")
            
            # Parse company size range
            min_employees, max_employees = self._parse_company_size(company_size)
            
            # Clean and validate seed companies
            validated_seeds = await self._validate_seed_companies(seed_companies)
            await self._update_progress(task_id, "validated_seeds", 5, f"Validated {len(validated_seeds)} seed companies")
            
            if not validated_seeds:
                raise ValueError("No valid seed companies provided")
            
            # Discovery phase
            await self._update_progress(task_id, "discovery", 10, "Starting company discovery...")
            
            for depth_level in range(1, crawl_depth + 1):
                companies_to_process = validated_seeds if depth_level == 1 else [c.name for c in self.discovered_companies[-20:]]
                
                for i, seed_company in enumerate(companies_to_process):
                    if len(self.discovered_companies) >= max_companies:
                        break
                        
                    progress = 10 + (depth_level - 1) * 30 + (i / len(companies_to_process)) * 30
                    await self._update_progress(
                        task_id, 
                        "discovery", 
                        min(progress, 70), 
                        f"Level {depth_level}: Discovering similar to {seed_company}..."
                    )
                    
                    similar_companies = await self._discover_similar_companies(
                        seed_company, industry, min_employees, max_employees
                    )
                    
                    for company in similar_companies:
                        if len(self.discovered_companies) >= max_companies:
                            break
                        if company.name.lower() not in self.processed_companies:
                            self.discovered_companies.append(company)
                            self.processed_companies.add(company.name.lower())
            
            # Filter existing companies if requested
            if skip_existing:
                await self._update_progress(task_id, "filtering", 75, "Filtering existing companies...")
                await self._filter_existing_companies()
            
            # Enrichment phase
            companies_enriched = 0
            if enable_enrichment and self.discovered_companies:
                await self._update_progress(task_id, "enrichment", 80, "Enriching company data...")
                companies_enriched = await self._enrich_discovered_companies()
            
            # Add companies to database
            await self._update_progress(task_id, "saving", 90, "Saving companies to database...")
            companies_added = await self._save_companies_to_database()
            
            # Lead scoring phase
            companies_scored = 0
            if enable_scoring and companies_added > 0:
                await self._update_progress(task_id, "scoring", 95, "Scoring companies for lead qualification...")
                companies_scored = await self._score_added_companies()
            
            # Final results
            results = {
                "status": "completed",
                "task_id": task_id,
                "stats": {
                    "companies_discovered": len(self.discovered_companies),
                    "companies_added": companies_added,
                    "companies_enriched": companies_enriched,
                    "companies_scored": companies_scored,
                },
                "preview": await self._generate_results_preview()
            }
            
            await self._update_progress(task_id, "completed", 100, "Crawling completed successfully!")
            return results
            
        except Exception as e:
            logger.error(f"Crawling error: {e}")
            await self._update_progress(task_id, "error", 0, f"Crawling failed: {str(e)}")
            raise
    
    def _parse_company_size(self, company_size: str) -> Tuple[int, int]:
        """Parse company size range string"""
        size_mapping = {
            "1-10": (1, 10),
            "11-50": (11, 50),
            "51-200": (51, 200),
            "201-1000": (201, 1000),
            "1000+": (1000, 50000)
        }
        return size_mapping.get(company_size, (50, 200))
    
    async def _validate_seed_companies(self, seed_companies: List[str]) -> List[str]:
        """Validate and clean seed company names/domains"""
        validated = []
        for company in seed_companies:
            company = company.strip()
            if company:
                # Remove common domain extensions to get company name
                if '.' in company and any(company.endswith(ext) for ext in ['.com', '.io', '.ai', '.net', '.org']):
                    company = company.split('.')[0]
                validated.append(company)
        return validated
    
    async def _discover_similar_companies(
        self, 
        seed_company: str, 
        industry: str, 
        min_employees: int, 
        max_employees: int
    ) -> List[DiscoveredCompany]:
        """Discover companies similar to the seed company using OpenAI"""
        
        prompt = f"""
        Find 8-10 companies similar to "{seed_company}" in the {industry} industry.
        
        Requirements:
        - Employee count between {min_employees} and {max_employees}
        - Operating companies (not defunct)
        - Similar business model or target market
        - Include both well-known and lesser-known companies
        - Focus on B2B companies that likely need customer support
        
        Return a JSON array with this structure:
        [
            {{
                "name": "Company Name",
                "domain": "company.com",
                "industry": "Software",
                "employee_count": 150,
                "location": "San Francisco, CA",
                "description": "Brief description of what they do",
                "similarity_score": 8.5
            }}
        ]
        
        Only return valid JSON, no other text.
        """
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2000
                )
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                companies_data = json.loads(json_match.group())
            else:
                companies_data = json.loads(content)
            
            discovered = []
            for company_data in companies_data:
                discovered.append(DiscoveredCompany(
                    name=company_data.get('name', ''),
                    domain=company_data.get('domain'),
                    industry=company_data.get('industry', industry),
                    employee_count=company_data.get('employee_count'),
                    location=company_data.get('location'),
                    description=company_data.get('description'),
                    similarity_score=company_data.get('similarity_score', 0.0),
                    discovery_method="openai_similar",
                    source_company=seed_company
                ))
            
            return discovered
            
        except Exception as e:
            logger.error(f"Error discovering similar companies for {seed_company}: {e}")
            return []
    
    async def _filter_existing_companies(self):
        """Remove companies that already exist in the database"""
        if not self.discovered_companies:
            return
            
        db = next(get_db_session())
        try:
            existing_names = set()
            existing_domains = set()
            
            # Get existing company names and domains
            existing_companies = db.query(Company).filter(Company.is_active == True).all()
            for company in existing_companies:
                if company.name:
                    existing_names.add(company.name.lower())
                if company.domain:
                    existing_domains.add(company.domain.lower())
            
            # Filter out existing companies
            filtered_companies = []
            for company in self.discovered_companies:
                is_duplicate = (
                    company.name.lower() in existing_names or
                    (company.domain and company.domain.lower() in existing_domains)
                )
                
                if not is_duplicate:
                    filtered_companies.append(company)
            
            logger.info(f"Filtered {len(self.discovered_companies) - len(filtered_companies)} existing companies")
            self.discovered_companies = filtered_companies
            
        finally:
            db.close()
    
    async def _enrich_discovered_companies(self) -> int:
        """Enrich discovered companies with additional data"""
        enriched_count = 0
        
        for company in self.discovered_companies:
            if not company.domain:
                try:
                    # Try to enrich the company to get domain and other data
                    enrichment_data = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.enricher.enrich_company_data,
                        company.name
                    )
                    
                    if enrichment_data:
                        company.domain = enrichment_data.get('domain', company.domain)
                        company.industry = enrichment_data.get('industry', company.industry)
                        company.employee_count = enrichment_data.get('employee_count', company.employee_count)
                        company.location = enrichment_data.get('location', company.location)
                        company.description = enrichment_data.get('description', company.description)
                        enriched_count += 1
                        
                except Exception as e:
                    logger.error(f"Error enriching {company.name}: {e}")
                    continue
                
                # Rate limiting
                await asyncio.sleep(0.5)
        
        return enriched_count
    
    async def _save_companies_to_database(self) -> int:
        """Save discovered companies to the database"""
        if not self.discovered_companies:
            return 0
            
        db = next(get_db_session())
        try:
            added_count = 0
            
            for company_data in self.discovered_companies:
                try:
                    # Create new company record
                    new_company = Company(
                        name=company_data.name,
                        domain=company_data.domain,
                        industry=company_data.industry,
                        employee_count=company_data.employee_count,
                        location=company_data.location,
                        source="lead_crawler",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    db.add(new_company)
                    db.commit()
                    added_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving company {company_data.name}: {e}")
                    db.rollback()
                    continue
            
            return added_count
            
        finally:
            db.close()
    
    async def _score_added_companies(self) -> int:
        """Score recently added companies for lead qualification"""
        db = next(get_db_session())
        try:
            # Get recently added companies from crawler that haven't been scored
            recent_companies = db.query(Company).filter(
                Company.source == "lead_crawler",
                Company.lead_scored_at.is_(None),
                Company.is_active == True
            ).limit(50).all()
            
            scored_count = 0
            
            for company in recent_companies:
                try:
                    # Score the company
                    score = await score_company_by_id(company.id)
                    if score:
                        save_lead_score_to_db(score)
                        scored_count += 1
                        
                except Exception as e:
                    logger.error(f"Error scoring company {company.name}: {e}")
                    continue
                    
                # Rate limiting
                await asyncio.sleep(0.5)
            
            return scored_count
            
        finally:
            db.close()
    
    async def _generate_results_preview(self) -> List[Dict]:
        """Generate a preview of discovered companies for the UI"""
        db = next(get_db_session())
        try:
            # Get recently added companies from crawler
            recent_companies = db.query(Company).filter(
                Company.source == "lead_crawler"
            ).order_by(Company.created_at.desc()).limit(10).all()
            
            preview = []
            for company in recent_companies:
                preview.append({
                    "name": company.name,
                    "domain": company.domain,
                    "industry": company.industry,
                    "employee_count": company.employee_count,
                    "lead_score": company.lead_score,
                    "is_qualified_lead": company.is_qualified_lead
                })
            
            return preview
            
        finally:
            db.close()
    
    async def _update_progress(self, task_id: str, stage: str, progress: float, message: str):
        """Update crawling progress"""
        if self.progress_callback:
            progress_data = CrawlingProgress(
                task_id=task_id,
                stage=stage,
                progress=progress,
                message=message,
                companies_discovered=len(self.discovered_companies),
                companies_added=getattr(self, '_companies_added', 0),
                companies_enriched=getattr(self, '_companies_enriched', 0),
                companies_scored=getattr(self, '_companies_scored', 0)
            )
            await self.progress_callback(progress_data)