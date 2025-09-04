#!/usr/bin/env python3
"""
FastAPI Backend for Lead Generation Tool
"""

from fastapi import FastAPI, BackgroundTasks, WebSocket, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.websockets import WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import json
import os
from datetime import datetime
import uuid
import logging
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ats_scraper import ATSScraper, CompanyLead
from company_seeder import CompanySeeder, CompanyProfile
from database import get_db_session, get_database_manager, health_check
from models import Company, JobPosting, ScrapingLog, SeedingSession
from openai_enricher import OpenAICompanyEnricher
from lead_scoring import LeadScoringEngine, score_company_by_id, save_lead_score_to_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Lead Generation Tool")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state
scraping_tasks = {}
active_connections: List[WebSocket] = []

class ScrapingConfig(BaseModel):
    companies: List[str] = []
    max_companies: Optional[int] = 10
    include_greenhouse: bool = True
    include_lever: bool = True
    min_support_roles: int = 1
    max_ai_roles: int = 0
    use_seeded_companies: bool = False
    
class SeedingConfig(BaseModel):
    target_count: int = 3000
    use_apollo: bool = False
    apollo_api_key: Optional[str] = None
    use_yc_data: bool = True
    min_employees: int = 50
    max_employees: int = 100
    exclude_ai_companies: bool = True

class CompanyCreate(BaseModel):
    name: str
    domain: str
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    founded_year: Optional[int] = None
    technology_stack: Optional[List[str]] = None
    linkedin_url: Optional[str] = None
    source: str = "manual"

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    founded_year: Optional[int] = None
    technology_stack: Optional[List[str]] = None
    linkedin_url: Optional[str] = None
    is_active: Optional[bool] = None

class CompanyIdBatch(BaseModel):
    company_ids: List[int]
    hard: Optional[bool] = True

class CompanyFilter(BaseModel):
    industry: Optional[str] = None
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    source: Optional[str] = None
    is_active: Optional[bool] = None
    is_qualified_lead: Optional[bool] = None
    ats_scraped: Optional[bool] = None
    search_term: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0

class EnrichmentRequest(BaseModel):
    company_ids: List[int]
    max_concurrent: Optional[int] = 3

class TenantCreationRequest(BaseModel):
    company_id: int

class ConfigUpdateRequest(BaseModel):
    tenant_api_url: str

class CrawlingConfig(BaseModel):
    seed_companies: List[str]
    industry: str
    company_size: str
    max_companies: Optional[int] = 50
    crawl_depth: Optional[int] = 2
    enable_enrichment: Optional[bool] = True
    enable_scoring: Optional[bool] = True
    skip_existing: Optional[bool] = True

class ScrapingStatus(BaseModel):
    task_id: str
    status: str  # "running", "completed", "failed"
    progress: int
    total: int
    current_company: Optional[str] = None
    leads_found: int = 0
    csv_file: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            # Remove broken connections
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        broken_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                broken_connections.append(connection)
        
        # Remove broken connections
        for connection in broken_connections:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    """Serve the main frontend page"""
    with open("static/index-refactored.html", "r") as f:
        return HTMLResponse(f.read())

@app.get("/api/company-count")
async def get_company_count(db: Session = Depends(get_db_session)):
    """Get count of seeded companies in the database"""
    try:
        count = db.query(Company).filter(Company.is_active == True).count()
        return {"count": count, "message": f"{count} companies available"}
    except Exception as e:
        logger.error(f"Error getting company count: {e}")
        return {"count": 0, "message": "Error checking database"}



@app.post("/api/seed-companies")
async def seed_companies(config: SeedingConfig, background_tasks: BackgroundTasks):
    """Seed the database with company data"""
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    scraping_tasks[task_id] = ScrapingStatus(
        task_id=task_id,
        status="running", 
        progress=0,
        total=config.target_count,
        leads_found=0,
        started_at=datetime.now()
    )
    
    # Start seeding task
    background_tasks.add_task(run_seeding_task, task_id, config)
    
    return {"task_id": task_id, "status": "seeding_started"}

@app.post("/api/start-scraping")
async def start_scraping(config: ScrapingConfig, background_tasks: BackgroundTasks):
    """Start a new scraping task"""
    task_id = str(uuid.uuid4())
    
    companies_to_scrape = config.companies
    
    # If using seeded companies, load from database
    if config.use_seeded_companies:
        companies_to_scrape = await load_seeded_companies_from_db(config.max_companies)
    
    # Initialize task status
    scraping_tasks[task_id] = ScrapingStatus(
        task_id=task_id,
        status="running",
        progress=0,
        total=len(companies_to_scrape),
        leads_found=0,
        started_at=datetime.now()
    )
    
    # Start background task
    background_tasks.add_task(run_scraping_task, task_id, config, companies_to_scrape)
    
    return {"task_id": task_id, "status": "started"}

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a scraping task"""
    if task_id not in scraping_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return scraping_tasks[task_id]

@app.get("/api/download/{task_id}")
async def download_csv(task_id: str):
    """Download the CSV file for a completed task"""
    if task_id not in scraping_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = scraping_tasks[task_id]
    if task.status != "completed" or not task.csv_file:
        raise HTTPException(status_code=400, detail="Task not completed or no CSV file available")
    
    if not os.path.exists(task.csv_file):
        raise HTTPException(status_code=404, detail="CSV file not found")
    
    return FileResponse(
        task.csv_file,
        media_type="text/csv",
        filename=f"leads_{task_id}.csv"
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back for now (could handle commands later)
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Database-powered Company CRUD API endpoints

@app.get("/api/health")
async def api_health_check():
    """Database health check endpoint"""
    return health_check()

@app.get("/api/companies")
async def get_companies(
    industry: Optional[str] = None,
    min_employees: Optional[int] = None,
    max_employees: Optional[int] = None,
    source: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_qualified_lead: Optional[bool] = None,
    ats_scraped: Optional[bool] = None,
    search_term: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session)
):
    """Get companies with filtering and pagination"""
    try:
        # Log incoming parameters
        logger.info(f"get_companies called with: search_term='{search_term}', limit={limit}, offset={offset}")
        
        query = db.query(Company)
        
        # Apply filters
        if industry:
            query = query.filter(Company.industry.ilike(f"%{industry}%"))
        if min_employees is not None:
            query = query.filter(Company.employee_count >= min_employees)
        if max_employees is not None:
            query = query.filter(Company.employee_count <= max_employees)
        if source:
            query = query.filter(Company.source == source)
        if is_active is not None:
            query = query.filter(Company.is_active == is_active)
        if is_qualified_lead is not None:
            query = query.filter(Company.is_qualified_lead == is_qualified_lead)
        if ats_scraped is not None:
            query = query.filter(Company.ats_scraped == ats_scraped)
        if search_term:
            search_filter = f"%{search_term}%"
            logger.info(f"Applying search filter: '{search_term}' -> SQL pattern: '{search_filter}'")
            query = query.filter(
                (Company.name.ilike(search_filter)) |
                (Company.domain.ilike(search_filter)) |
                (Company.location.ilike(search_filter))
            )
            logger.info(f"Search filter applied to query")
        else:
            logger.info("No search term provided")
        
        # Log the final query state
        # logger.info(f"Final query filters applied. Base query: {query}")
        
        # Get total count for pagination
        total_count = query.count()
        logger.info(f"Total companies matching filters: {total_count}")
        
        # Apply ordering: lead-scored first, highest score next, then newest
        companies = query.order_by(
            Company.lead_scored_at.is_(None),  # non-null first
            Company.lead_score.desc(),
            Company.created_at.desc()
        ).offset(offset).limit(limit).all()
        logger.info(f"Returning {len(companies)} companies (limit: {limit}, offset: {offset})")
        
        # Log first few company names for debugging
        if companies:
            company_names = [c.name for c in companies[:3]]
            logger.info(f"First 3 companies in results: {company_names}")
            
            # Check if search results actually contain the search term
            if search_term:
                matching_companies = [c for c in companies if 
                    search_term.lower() in c.name.lower() or 
                    search_term.lower() in (c.domain or '').lower() or 
                    search_term.lower() in (c.location or '').lower()]
                logger.info(f"Search term '{search_term}' found in {len(matching_companies)} out of {len(companies)} returned companies")
        
        return {
            "companies": [company.to_dict() for company in companies],
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch companies: {str(e)}")

@app.get("/api/companies/{company_id}")
async def get_company(company_id: int, db: Session = Depends(get_db_session)):
    """Get a specific company by ID"""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        return company.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch company: {str(e)}")

@app.post("/api/companies")
async def create_company(company_data: CompanyCreate, db: Session = Depends(get_db_session)):
    """Create a new company"""
    try:
        # Check if company with domain already exists
        existing = db.query(Company).filter(Company.domain == company_data.domain).first()
        if existing:
            raise HTTPException(status_code=400, detail="Company with this domain already exists")
        
        # Create new company
        company = Company(
            name=company_data.name,
            domain=company_data.domain,
            industry=company_data.industry,
            employee_count=company_data.employee_count,
            location=company_data.location,
            founded_year=company_data.founded_year,
            technology_stack=company_data.technology_stack or [],
            linkedin_url=company_data.linkedin_url,
            source=company_data.source
        )
        
        db.add(company)
        db.commit()
        db.refresh(company)
        
        logger.info(f"Created company: {company.name} ({company.domain})")
        return company.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating company: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create company: {str(e)}")

@app.put("/api/companies/{company_id}")
async def update_company(
    company_id: int, 
    company_data: CompanyUpdate, 
    db: Session = Depends(get_db_session)
):
    """Update an existing company"""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Update fields if provided
        update_data = company_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(company, field, value)
        
        db.commit()
        db.refresh(company)
        
        logger.info(f"Updated company: {company.name} ({company.domain})")
        return company.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update company: {str(e)}")

@app.delete("/api/companies/{company_id}")
async def delete_company(company_id: int, db: Session = Depends(get_db_session)):
    """Delete a company (soft delete - marks as inactive)"""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Soft delete by marking as inactive
        company.is_active = False
        db.commit()
        
        logger.info(f"Soft deleted company: {company.name} ({company.domain})")
        return {"message": "Company marked as inactive", "company_id": company_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete company: {str(e)}")

@app.post("/api/companies/delete-batch")
async def delete_companies_batch(payload: CompanyIdBatch, db: Session = Depends(get_db_session)):
    """Hard delete companies and all associated data (job postings, logs)."""
    try:
        if not payload.company_ids:
            raise HTTPException(status_code=400, detail="No company IDs provided")
        deleted = 0
        for cid in payload.company_ids:
            company = db.query(Company).filter(Company.id == cid).first()
            if not company:
                continue
            # Delete associated data explicitly
            db.query(JobPosting).filter(JobPosting.company_id == cid).delete(synchronize_session=False)
            db.query(ScrapingLog).filter(ScrapingLog.company_id == cid).delete(synchronize_session=False)
            # Delete company
            db.delete(company)
            deleted += 1
        db.commit()
        return {"deleted_companies": deleted, "requested": len(payload.company_ids), "company_ids": payload.company_ids}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting companies batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete companies: {str(e)}")

@app.get("/api/companies/{company_id}/jobs")
async def get_company_jobs(company_id: int, db: Session = Depends(get_db_session)):
    """Get all job postings for a specific company"""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        jobs = db.query(JobPosting).filter(
            JobPosting.company_id == company_id,
            JobPosting.is_active == True
        ).order_by(JobPosting.created_at.desc()).all()
        
        return {
            "company": company.to_dict(),
            "jobs": [job.to_dict() for job in jobs],
            "total_jobs": len(jobs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching jobs for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")

@app.get("/api/companies/{company_id}/logs")
async def get_company_logs(company_id: int, db: Session = Depends(get_db_session)):
    """Get scraping logs for a specific company"""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        logs = db.query(ScrapingLog).filter(
            ScrapingLog.company_id == company_id
        ).order_by(ScrapingLog.started_at.desc()).all()
        
        return {
            "company": company.to_dict(),
            "logs": [log.to_dict() for log in logs],
            "total_logs": len(logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching logs for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")

@app.get("/api/stats")
async def get_database_stats(db: Session = Depends(get_db_session)):
    """Get database statistics and summary"""
    try:
        from sqlalchemy import func
        
        # Company stats
        total_companies = db.query(Company).count()
        active_companies = db.query(Company).filter(Company.is_active == True).count()
        scraped_companies = db.query(Company).filter(Company.ats_scraped == True).count()
        qualified_leads = db.query(Company).filter(Company.is_qualified_lead == True).count()
        
        # Job posting stats
        total_jobs = db.query(JobPosting).count()
        support_jobs = db.query(JobPosting).filter(JobPosting.role_category == 'support').count()
        sales_jobs = db.query(JobPosting).filter(JobPosting.role_category == 'sales').count()
        ai_jobs = db.query(JobPosting).filter(JobPosting.role_category == 'ai').count()
        
        # Source breakdown
        source_counts = db.query(
            Company.source,
            func.count(Company.id)
        ).group_by(Company.source).all()
        
        # Industry breakdown (top 10)
        industry_counts = db.query(
            Company.industry,
            func.count(Company.id)
        ).filter(Company.industry.isnot(None)).group_by(
            Company.industry
        ).order_by(func.count(Company.id).desc()).limit(10).all()
        
        return {
            "companies": {
                "total": total_companies,
                "active": active_companies,
                "scraped": scraped_companies,
                "qualified_leads": qualified_leads
            },
            "jobs": {
                "total": total_jobs,
                "support": support_jobs,
                "sales": sales_jobs,
                "ai": ai_jobs
            },
            "sources": {source: count for source, count in source_counts},
            "top_industries": {industry: count for industry, count in industry_counts}
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

# Company Enrichment API endpoints

@app.post("/api/companies/{company_id}/enrich")
async def enrich_single_company(company_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db_session)):
    """Enrich a single company with OpenAI web search"""
    try:
        # Check if company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Create task ID for tracking
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        scraping_tasks[task_id] = ScrapingStatus(
            task_id=task_id,
            status="running",
            progress=0,
            total=1,
            current_company=company.name,
            leads_found=0,
            started_at=datetime.now()
        )
        
        # Start enrichment task
        background_tasks.add_task(run_enrichment_task, task_id, [company_id])
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Enrichment started for {company.name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting enrichment for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start enrichment: {str(e)}")

@app.post("/api/companies/enrich-batch")
async def enrich_companies_batch(
    request: EnrichmentRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
):
    """Enrich multiple companies in batch"""
    try:
        # Validate company IDs exist
        companies = db.query(Company).filter(Company.id.in_(request.company_ids)).all()
        found_ids = {c.id for c in companies}
        missing_ids = set(request.company_ids) - found_ids
        
        if missing_ids:
            raise HTTPException(
                status_code=404, 
                detail=f"Companies not found: {list(missing_ids)}"
            )
        
        # Create task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        scraping_tasks[task_id] = ScrapingStatus(
            task_id=task_id,
            status="running",
            progress=0,
            total=len(request.company_ids),
            leads_found=0,
            started_at=datetime.now()
        )
        
        # Start batch enrichment task
        background_tasks.add_task(
            run_enrichment_task, 
            task_id, 
            request.company_ids, 
            request.max_concurrent
        )
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Batch enrichment started for {len(request.company_ids)} companies"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch enrichment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start batch enrichment: {str(e)}")

@app.post("/api/companies/enrich-missing-domains")
async def enrich_missing_domains(
    limit: Optional[int] = 10,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db_session)
):
    """Enrich companies that don't have domains"""
    try:
        # Find companies without domains
        companies = db.query(Company).filter(
            Company.domain.is_(None),
            Company.is_active == True
        ).limit(limit).all()
        
        if not companies:
            return {
                "message": "No companies found without domains",
                "count": 0
            }
        
        company_ids = [c.id for c in companies]
        
        # Create task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        scraping_tasks[task_id] = ScrapingStatus(
            task_id=task_id,
            status="running",
            progress=0,
            total=len(company_ids),
            leads_found=0,
            started_at=datetime.now()
        )
        
        # Start enrichment task
        background_tasks.add_task(run_enrichment_task, task_id, company_ids, 2)  # Lower concurrency
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Enrichment started for {len(company_ids)} companies without domains",
            "companies": [{"id": c.id, "name": c.name} for c in companies]
        }
        
    except Exception as e:
        logger.error(f"Error starting missing domains enrichment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start enrichment: {str(e)}")

async def run_enrichment_task(task_id: str, company_ids: List[int], max_concurrent: int = 3):
    """Background task to run company enrichment"""
    try:
        logger.info(f"Starting enrichment task {task_id} for companies: {company_ids}")
        
        # Initialize enricher
        try:
            enricher = OpenAICompanyEnricher()
            logger.info(f"OpenAI enricher initialized successfully for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI enricher for task {task_id}: {e}")
            raise
        
        task = scraping_tasks[task_id]
        
        # Broadcast start message
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "status",
            "message": f"Starting enrichment for {len(company_ids)} companies..."
        }))
        logger.info(f"Sent start broadcast for task {task_id}")
        
        successful_enrichments = 0
        
        for i, company_id in enumerate(company_ids):
            try:
                logger.info(f"Task {task_id}: Processing company {i+1}/{len(company_ids)} (ID: {company_id})")
                
                # Update progress
                task.progress = i
                task.current_company = f"Company ID {company_id}"
                
                # Broadcast progress
                await manager.broadcast(json.dumps({
                    "task_id": task_id,
                    "type": "progress",
                    "progress": i,
                    "total": len(company_ids),
                    "current_company": f"Enriching company {company_id}"
                }))
                logger.info(f"Task {task_id}: Sent progress broadcast for company {company_id}")
                
                # Enrich company
                logger.info(f"Task {task_id}: Starting enrichment for company {company_id}")
                result = enricher.enrich_company_by_id(company_id)
                logger.info(f"Task {task_id}: Enrichment result for company {company_id}: {result}")
                
                if 'error' not in result:
                    successful_enrichments += 1
                    await manager.broadcast(json.dumps({
                        "task_id": task_id,
                        "type": "enrichment_success",
                        "message": f"Successfully enriched company {company_id}",
                        "company_id": company_id
                    }))
                    logger.info(f"Task {task_id}: Successfully enriched company {company_id}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Task {task_id}: Failed to enrich company {company_id}: {error_msg}")
                    await manager.broadcast(json.dumps({
                        "task_id": task_id,
                        "type": "enrichment_error",
                        "message": f"Failed to enrich company {company_id}: {error_msg}",
                        "company_id": company_id
                    }))
                
                # Rate limiting delay
                logger.info(f"Task {task_id}: Rate limiting delay (2 seconds)")
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Task {task_id}: Exception enriching company {company_id}: {e}", exc_info=True)
                await manager.broadcast(json.dumps({
                    "task_id": task_id,
                    "type": "enrichment_error",
                    "message": f"Error enriching company {company_id}: {str(e)}",
                    "company_id": company_id
                }))
        
        # Update task completion
        logger.info(f"Task {task_id}: Completing task. Success: {successful_enrichments}/{len(company_ids)}")
        task.status = "completed"
        task.progress = len(company_ids)
        task.completed_at = datetime.now()
        task.leads_found = successful_enrichments
        
        # Broadcast completion
        completion_message = {
            "task_id": task_id,
            "type": "completed",
            "message": f"Enrichment completed! Successfully enriched {successful_enrichments}/{len(company_ids)} companies.",
            "successful": successful_enrichments,
            "total": len(company_ids)
        }
        await manager.broadcast(json.dumps(completion_message))
        logger.info(f"Task {task_id}: Sent completion broadcast: {completion_message}")
        
    except Exception as e:
        # Handle task failure
        logger.error(f"Task {task_id}: Task failed with exception: {e}", exc_info=True)
        task = scraping_tasks[task_id]
        task.status = "failed"
        task.completed_at = datetime.now()
        
        error_message = {
            "task_id": task_id,
            "type": "error",
            "message": f"Enrichment failed: {str(e)}"
        }
        await manager.broadcast(json.dumps(error_message))
        logger.error(f"Task {task_id}: Sent error broadcast: {error_message}")

# Tenant Creation API endpoints

@app.post("/api/companies/{company_id}/create-tenant")
async def create_tenant_for_company(company_id: int, db: Session = Depends(get_db_session)):
    """Create a tenant using the external API for a company"""
    try:
        # Check if company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check if lead scoring is complete
        if not company.lead_scored_at:
            raise HTTPException(status_code=400, detail="Lead scoring must be completed before creating a tenant")
        
        # If tenant already exists, allow recreation but log it
        if company.tenant_id:
            logger.info(f"Recreating tenant for company {company_id}: {company.name} (previous tenant_id: {company.tenant_id})")
        
        # Prepare data for external API
        api_data = {
            "email": f"admin@{company.domain}" if company.domain else f"admin@{company.name.lower().replace(' ', '')}.com",
            "password": "TempPassword123!",
            "company_name": company.name,
            "website_url": f"https://{company.domain}" if company.domain else None
        }
        
        # Call external API - configurable via environment variables
        api_url = os.getenv('TENANT_CREATION_API_URL', 'http://localhost:9000/api/v1/external/create-tenant')
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"Creating tenant for company {company_id}: {company.name}")
        response = requests.post(api_url, json=api_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # Update company with tenant ID
                company.tenant_id = result['tenant_id']
                company.tenant_created_at = datetime.now()
                db.commit()
                
                logger.info(f"Successfully created tenant for company {company_id}: {result['tenant_id']}")
                return {
                    "success": True,
                    "tenant_id": result['tenant_id'],
                    "control_panel_url": result.get('control_panel_url'),
                    "message": f"Tenant created successfully for {company.name}"
                }
            else:
                error_msg = result.get('message', 'Unknown error from API')
                logger.error(f"API returned success=false for company {company_id}: {error_msg}")
                raise HTTPException(status_code=400, detail=f"Tenant creation failed: {error_msg}")
        else:
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            logger.error(f"Failed to create tenant for company {company_id}: {error_msg}")
            raise HTTPException(status_code=500, detail=f"External API error: {error_msg}")
            
    except requests.RequestException as e:
        logger.error(f"Network error creating tenant for company {company_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to tenant creation service: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating tenant for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create tenant: {str(e)}")

# Configuration API endpoints

@app.get("/api/config")
async def get_current_config():
    """Get current configuration settings"""
    return {
        "tenant_api_url": os.getenv('TENANT_CREATION_API_URL', 'http://localhost:9000/api/v1/external/create-tenant')
    }

@app.post("/api/config")
async def update_config(config: ConfigUpdateRequest):
    """Update configuration settings (this updates environment for current session only)"""
    try:
        # For development, we can update the environment variable for the current session
        os.environ['TENANT_CREATION_API_URL'] = config.tenant_api_url
        
        return {
            "success": True,
            "message": "Configuration updated successfully",
            "tenant_api_url": config.tenant_api_url
        }
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

# Lead Scoring API endpoints

@app.post("/api/companies/{company_id}/score")
async def score_single_company(
    company_id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db_session)
):
    """Score a single company using advanced lead scoring system"""
    try:
        # Check if company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        # Require domain for lead scoring
        if not company.domain:
            raise HTTPException(status_code=400, detail="Company domain is required for lead scoring. Please enrich first.")
        
        # Create task ID for tracking
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        scraping_tasks[task_id] = ScrapingStatus(
            task_id=task_id,
            status="running",
            progress=0,
            total=1,
            current_company=company.name,
            leads_found=0,
            started_at=datetime.now()
        )
        
        # Start lead scoring task
        background_tasks.add_task(run_lead_scoring_task, task_id, [company_id])
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Lead scoring started for {company.name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting lead scoring for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start lead scoring: {str(e)}")

@app.post("/api/companies/score-batch")
async def score_companies_batch(
    company_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
):
    """Score multiple companies using advanced lead scoring"""
    try:
        # Validate company IDs exist
        companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
        found_ids = {c.id for c in companies}
        missing_ids = set(company_ids) - found_ids
        
        if missing_ids:
            raise HTTPException(
                status_code=404, 
                detail=f"Companies not found: {list(missing_ids)}"
            )
        
        # Create task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        scraping_tasks[task_id] = ScrapingStatus(
            task_id=task_id,
            status="running",
            progress=0,
            total=len(company_ids),
            leads_found=0,
            started_at=datetime.now()
        )
        
        # Start batch lead scoring task
        background_tasks.add_task(run_lead_scoring_task, task_id, company_ids)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Batch lead scoring started for {len(company_ids)} companies"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch lead scoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start batch lead scoring: {str(e)}")

@app.post("/api/companies/score-unscored")
async def score_unscored_companies(
    limit: Optional[int] = 20,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db_session)
):
    """Score companies that haven't been scored yet"""
    try:
        # Find companies without lead scores
        companies = db.query(Company).filter(
            Company.lead_scored_at.is_(None),
            Company.is_active == True,
            Company.domain.isnot(None),
            Company.domain != ''
        ).limit(limit).all()
        
        if not companies:
            return {
                "message": "No unscored companies found",
                "count": 0
            }
        
        company_ids = [c.id for c in companies]
        
        # Create task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        scraping_tasks[task_id] = ScrapingStatus(
            task_id=task_id,
            status="running",
            progress=0,
            total=len(company_ids),
            leads_found=0,
            started_at=datetime.now()
        )
        
        # Start scoring task
        background_tasks.add_task(run_lead_scoring_task, task_id, company_ids)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Lead scoring started for {len(company_ids)} unscored companies",
            "companies": [{"id": c.id, "name": c.name} for c in companies]
        }
        
    except Exception as e:
        logger.error(f"Error starting unscored companies scoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scoring: {str(e)}")

@app.get("/api/companies/top-leads")
async def get_top_leads(
    limit: Optional[int] = 50,
    min_score: Optional[int] = 200,
    db: Session = Depends(get_db_session)
):
    """Get top-scoring leads with filtering"""
    try:
        query = db.query(Company).filter(
            Company.is_active == True,
            Company.lead_scored_at.isnot(None)
        )
        
        if min_score:
            query = query.filter(Company.lead_score >= min_score)
        
        companies = query.order_by(Company.lead_score.desc()).limit(limit).all()
        
        return {
            "companies": [company.to_dict() for company in companies],
            "total": len(companies),
            "filters_applied": {
                "min_score": min_score,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching top leads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top leads: {str(e)}")

async def run_lead_scoring_task(task_id: str, company_ids: List[int]):
    """Background task to run lead scoring"""
    try:
        logger.info(f"Starting lead scoring task {task_id} for companies: {company_ids}")
        
        task = scraping_tasks[task_id]
        
        # Broadcast start message
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "status",
            "message": f"Starting lead scoring for {len(company_ids)} companies..."
        }))
        
        successful_scores = 0
        
        for i, company_id in enumerate(company_ids):
            try:
                logger.info(f"Task {task_id}: Scoring company {i+1}/{len(company_ids)} (ID: {company_id})")
                # Domain requirement check
                try:
                    db = next(get_db_session())
                    company = db.query(Company).filter(Company.id == company_id).first()
                    if not company or not company.domain:
                        logger.warning(f"Task {task_id}: Skipping company {company_id} due to missing domain")
                        await manager.broadcast(json.dumps({
                            "task_id": task_id,
                            "type": "error",
                            "message": f"Skipping company {company_id}: domain is missing",
                            "company_id": company_id
                        }))
                        continue
                except Exception as chk_err:
                    logger.error(f"Task {task_id}: Error checking domain for {company_id}: {chk_err}")
                    continue
                
                # Update progress
                task.progress = i
                task.current_company = f"Company ID {company_id}"
                
                # Broadcast progress
                await manager.broadcast(json.dumps({
                    "task_id": task_id,
                    "type": "progress",
                    "progress": i,
                    "total": len(company_ids),
                    "current_company": f"Scoring company {company_id}"
                }))
                
                # Score company with phase progress callback
                logger.info(f"Task {task_id}: Starting lead scoring for company {company_id}")

                async def phase_callback(phase_key: str, index: int, total: int):
                    try:
                        await manager.broadcast(json.dumps({
                            "task_id": task_id,
                            "type": "lead_scoring_phase",
                            "phase": phase_key,
                            "index": index,
                            "total": total,
                            "company_id": company_id
                        }))
                    except Exception as e:
                        logger.warning(f"Failed broadcasting phase {phase_key}: {e}")

                score = await score_company_by_id(company_id, phase_callback)
                
                # Save to database
                save_lead_score_to_db(score)
                
                successful_scores += 1
                
                await manager.broadcast(json.dumps({
                    "task_id": task_id,
                    "type": "lead_found",
                    "message": f"Company {company_id} scored: {score.overall_score}/400",
                    "company_id": company_id,
                    "score": score.overall_score
                }))
                
                logger.info(f"Task {task_id}: Successfully scored company {company_id} - {score.overall_score}/400")
                
                # Rate limiting delay
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Task {task_id}: Exception scoring company {company_id}: {e}", exc_info=True)
                await manager.broadcast(json.dumps({
                    "task_id": task_id,
                    "type": "error",
                    "message": f"Error scoring company {company_id}: {str(e)}",
                    "company_id": company_id
                }))
        
        # Update task completion
        task.status = "completed"
        task.progress = len(company_ids)
        task.completed_at = datetime.now()
        task.leads_found = successful_scores
        
        # Broadcast completion
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "completed",
            "message": f"Lead scoring completed! Successfully scored {successful_scores}/{len(company_ids)} companies.",
            "successful": successful_scores,
            "total": len(company_ids)
        }))
        
    except Exception as e:
        # Handle task failure
        logger.error(f"Task {task_id}: Lead scoring task failed: {e}", exc_info=True)
        task = scraping_tasks[task_id]
        task.status = "failed"
        task.completed_at = datetime.now()
        
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "error",
            "message": f"Lead scoring failed: {str(e)}"
        }))

def load_seeded_companies(max_companies: int = None) -> List[str]:
    """Load seeded companies from CSV file"""
    companies = []
    csv_file = "data/qualified_seed_companies.csv"
    
    if not os.path.exists(csv_file):
        logger.warning(f"Seeded companies file not found: {csv_file}")
        return []
    
    try:
        import csv as csv_module
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv_module.DictReader(file)
            for row in reader:
                if row.get('domain'):
                    # Extract company slug from domain for ATS scraping
                    domain = row['domain'].replace('.com', '').replace('.io', '').replace('.co', '')
                    companies.append(domain)
                    
                    if max_companies and len(companies) >= max_companies:
                        break
    except Exception as e:
        logger.error(f"Error loading seeded companies: {e}")
    
    return companies

async def load_seeded_companies_from_db(max_companies: int = None) -> List[str]:
    """Load seeded companies from database"""
    try:
        db = next(get_db_session())
        query = db.query(Company).filter(Company.is_active == True)
        
        if max_companies:
            query = query.limit(max_companies)
        
        companies = query.all()
        
        # Extract company domains for ATS scraping
        company_domains = []
        for company in companies:
            domain = company.domain.replace('.com', '').replace('.io', '').replace('.co', '')
            company_domains.append(domain)
        
        return company_domains
        
    except Exception as e:
        logger.error(f"Error loading seeded companies from database: {e}")
        return []
    finally:
        db.close()

async def run_seeding_task(task_id: str, config: SeedingConfig):
    """Background task to seed companies"""
    try:
        seeder = CompanySeeder()
        
        # Update task status
        task = scraping_tasks[task_id]
        
        # Broadcast start message
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "status",
            "message": "Starting company seeding process..."
        }))
        
        all_companies = []
        
        # Seed from Apollo if enabled and API key available
        if config.use_apollo and config.apollo_api_key:
            # Temporarily set the API key
            original_key = os.environ.get('APOLLO_API_KEY')
            os.environ['APOLLO_API_KEY'] = config.apollo_api_key
            
            await manager.broadcast(json.dumps({
                "task_id": task_id,
                "type": "log",
                "message": "Fetching companies from Apollo.io..."
            }))
            
            try:
                apollo_companies = seeder.seed_from_apollo(target_count=config.target_count)
                all_companies.extend(apollo_companies)
                
                await manager.broadcast(json.dumps({
                    "task_id": task_id,
                    "type": "progress",
                    "progress": len(apollo_companies),
                    "total": config.target_count,
                    "current_company": f"Apollo: {len(apollo_companies)} companies"
                }))
            finally:
                # Restore original API key
                if original_key:
                    os.environ['APOLLO_API_KEY'] = original_key
                else:
                    os.environ.pop('APOLLO_API_KEY', None)
        
        # Add Y Combinator data if enabled
        if config.use_yc_data:
            await manager.broadcast(json.dumps({
                "task_id": task_id,
                "type": "log",
                "message": "Adding Y Combinator companies..."
            }))
            
            yc_companies = seeder.seed_from_yc_companies()
            all_companies.extend(yc_companies)
            
            await manager.broadcast(json.dumps({
                "task_id": task_id,
                "type": "log",
                "message": f"Added {len(yc_companies)} Y Combinator companies"
            }))
        
        # Remove duplicates
        unique_companies = {}
        for company in all_companies:
            if company.domain not in unique_companies:
                unique_companies[company.domain] = company
        all_companies = list(unique_companies.values())
        
        # Apply filters
        filtered_companies = seeder.filter_companies(
            all_companies,
            min_employees=config.min_employees,
            max_employees=config.max_employees,
            exclude_industries=['AI/ML', 'Machine Learning'] if config.exclude_ai_companies else []
        )
        
        # Save to database
        db = next(get_db_session())
        try:
            companies_saved = 0
            for company_profile in filtered_companies:
                # Check if company already exists
                existing = db.query(Company).filter(Company.domain == company_profile.domain).first()
                if not existing:
                    # Create new company
                    company = Company(
                        name=company_profile.name,
                        domain=company_profile.domain,
                        industry=company_profile.industry,
                        employee_count=company_profile.employee_count,
                        location=company_profile.location,
                        founded_year=company_profile.founded_year,
                        technology_stack=company_profile.technology_stack or [],
                        linkedin_url=company_profile.linkedin_url,
                        source=company_profile.source,
                        is_active=True
                    )
                    db.add(company)
                    companies_saved += 1
            
            db.commit()
            
            # Update task completion
            task.status = "completed"
            task.progress = len(filtered_companies)
            task.completed_at = datetime.now()
            task.leads_found = companies_saved
            
            # Broadcast completion
            await manager.broadcast(json.dumps({
                "task_id": task_id,
                "type": "completed",
                "message": f"Company seeding completed! Seeded {companies_saved} qualified companies to database.",
                "leads_found": companies_saved
            }))
            
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error during seeding: {db_error}")
            raise db_error
        finally:
            db.close()
        

        
    except Exception as e:
        # Handle task failure
        task = scraping_tasks[task_id]
        task.status = "failed"
        task.completed_at = datetime.now()
        
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "error",
            "message": f"Seeding failed: {str(e)}"
        }))

async def run_scraping_task(task_id: str, config: ScrapingConfig, companies_to_scrape: List[str] = None):
    """Background task to run the scraping process"""
    try:
        scraper = ATSScraper()
        all_leads = []
        
        # Update task status
        task = scraping_tasks[task_id]
        
        # Broadcast start message
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "status",
            "message": "Starting scraping process..."
        }))
        
        if companies_to_scrape is None:
            companies_to_scrape = config.companies
            
        companies_to_scrape = companies_to_scrape[:config.max_companies] if config.max_companies else companies_to_scrape
        
        for i, company in enumerate(companies_to_scrape):
            # Update progress
            task.progress = i
            task.current_company = company
            
            # Broadcast progress update
            await manager.broadcast(json.dumps({
                "task_id": task_id,
                "type": "progress",
                "progress": i,
                "total": len(companies_to_scrape),
                "current_company": company
            }))
            
            jobs = []
            
            # Try Greenhouse if enabled
            if config.include_greenhouse:
                try:
                    await manager.broadcast(json.dumps({
                        "task_id": task_id,
                        "type": "log",
                        "message": f"Scraping Greenhouse for {company}..."
                    }))
                    gh_jobs = scraper.scrape_greenhouse_board(company)
                    jobs.extend(gh_jobs)
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    await manager.broadcast(json.dumps({
                        "task_id": task_id,
                        "type": "error",
                        "message": f"Greenhouse error for {company}: {str(e)}"
                    }))
            
            # Try Lever if enabled
            if config.include_lever:
                try:
                    await manager.broadcast(json.dumps({
                        "task_id": task_id,
                        "type": "log",
                        "message": f"Scraping Lever for {company}..."
                    }))
                    lever_jobs = scraper.scrape_lever_board(company)
                    jobs.extend(lever_jobs)
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    await manager.broadcast(json.dumps({
                        "task_id": task_id,
                        "type": "error",
                        "message": f"Lever error for {company}: {str(e)}"
                    }))
            
            # Analyze jobs if found
            if jobs:
                lead = scraper.analyze_company_jobs(jobs)
                if lead and lead.support_roles >= config.min_support_roles and lead.ai_roles <= config.max_ai_roles:
                    all_leads.append(lead)
                    task.leads_found = len(all_leads)
                    
                    await manager.broadcast(json.dumps({
                        "task_id": task_id,
                        "type": "lead_found",
                        "message": f"Found qualified lead: {lead.company} ({lead.support_roles} support roles)",
                        "leads_found": len(all_leads)
                    }))
        
        # Filter and sort leads
        qualified_leads = [lead for lead in all_leads 
                          if lead.support_roles >= config.min_support_roles and lead.ai_roles <= config.max_ai_roles]
        qualified_leads.sort(key=lambda x: (x.support_roles + x.sales_roles), reverse=True)
        
        # Save to CSV
        csv_filename = f"results/leads_{task_id}.csv"
        os.makedirs("results", exist_ok=True)
        
        scraper.save_results_to_csv(qualified_leads, csv_filename)
        
        # Update task completion
        task.status = "completed"
        task.progress = len(companies_to_scrape)
        task.csv_file = csv_filename
        task.completed_at = datetime.now()
        task.leads_found = len(qualified_leads)
        
        # Broadcast completion
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "completed",
            "message": f"Scraping completed! Found {len(qualified_leads)} qualified leads.",
            "csv_file": csv_filename,
            "leads_found": len(qualified_leads)
        }))
        
    except Exception as e:
        # Handle task failure
        task = scraping_tasks[task_id]
        task.status = "failed"
        task.completed_at = datetime.now()
        
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "error",
            "message": f"Scraping failed: {str(e)}"
        }))

# ==========================================
# Lead Crawling Endpoints
# ==========================================

@app.post("/api/start-crawling")
async def start_crawling(config: CrawlingConfig, background_tasks: BackgroundTasks):
    """Start a new lead crawling task"""
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    scraping_tasks[task_id] = ScrapingStatus(
        task_id=task_id,
        status="running",
        progress=0,
        total=config.max_companies,
        leads_found=0,
        started_at=datetime.now()
    )
    
    # Start crawling task
    background_tasks.add_task(run_crawling_task, task_id, config)
    
    return {"task_id": task_id, "status": "crawling_started"}

@app.post("/api/stop-crawling/{task_id}")
async def stop_crawling(task_id: str):
    """Stop a running crawling task"""
    if task_id in scraping_tasks:
        task = scraping_tasks[task_id]
        if task.status == "running":
            task.status = "stopped"
            task.completed_at = datetime.now()
            
            await manager.broadcast(json.dumps({
                "task_id": task_id,
                "type": "stopped",
                "message": "Crawling stopped by user"
            }))
            
            return {"status": "stopped"}
    
    raise HTTPException(status_code=404, detail="Task not found or not running")

@app.get("/api/download-crawling/{task_id}")
async def download_crawling_results(task_id: str):
    """Download crawling results as CSV"""
    if task_id not in scraping_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = scraping_tasks[task_id]
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")
    
    # Generate CSV of recently crawled companies
    db = next(get_db_session())
    try:
        companies = db.query(Company).filter(
            Company.source == "lead_crawler"
        ).order_by(Company.created_at.desc()).limit(task.total).all()
        
        if not companies:
            raise HTTPException(status_code=404, detail="No crawled companies found")
        
        # Generate CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Company', 'Domain', 'Industry', 'Employee Count', 'Location',
            'Lead Score', 'Qualified Lead', 'Created At', 'Source'
        ])
        
        # Data rows
        for company in companies:
            writer.writerow([
                company.name,
                company.domain or '',
                company.industry or '',
                company.employee_count or '',
                company.location or '',
                company.lead_score,
                'Yes' if company.is_qualified_lead else 'No',
                company.created_at.strftime('%Y-%m-%d %H:%M:%S') if company.created_at else '',
                company.source
            ])
        
        # Prepare file response
        from fastapi.responses import Response
        
        output.seek(0)
        content = output.getvalue()
        
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=crawler_results_{task_id}.csv"}
        )
        
    finally:
        db.close()

async def run_crawling_task(task_id: str, config: CrawlingConfig):
    """Background task for lead crawling"""
    
    try:
        # Import here to avoid circular imports
        from lead_crawler import LeadCrawler
        import os
        
        # Get OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Create progress callback
        async def progress_callback(progress_data):
            # Update task status
            task = scraping_tasks[task_id]
            task.progress = int(progress_data.progress)
            task.current_company = progress_data.message
            
            # Broadcast progress
            await manager.broadcast(json.dumps({
                "task_id": task_id,
                "type": "progress",
                "stage": progress_data.stage,
                "progress": progress_data.progress,
                "message": progress_data.message,
                "companies_discovered": progress_data.companies_discovered,
                "companies_added": progress_data.companies_added,
                "companies_enriched": progress_data.companies_enriched,
                "companies_scored": progress_data.companies_scored
            }))
        
        # Initialize crawler
        crawler = LeadCrawler(openai_api_key, progress_callback)
        
        # Start crawling
        results = await crawler.crawl_similar_companies(
            task_id=task_id,
            seed_companies=config.seed_companies,
            industry=config.industry,
            company_size=config.company_size,
            max_companies=config.max_companies,
            crawl_depth=config.crawl_depth,
            enable_enrichment=config.enable_enrichment,
            enable_scoring=config.enable_scoring,
            skip_existing=config.skip_existing
        )
        
        # Update task completion
        task = scraping_tasks[task_id]
        task.status = "completed"
        task.progress = 100
        task.completed_at = datetime.now()
        task.leads_found = results["stats"]["companies_added"]
        
        # Broadcast completion
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "completed",
            "status": "completed",
            "message": "Lead crawling completed successfully!",
            "stats": results["stats"],
            "preview": results["preview"]
        }))
        
    except Exception as e:
        logger.error(f"Crawling task {task_id} failed: {e}", exc_info=True)
        
        # Update task failure
        task = scraping_tasks[task_id]
        task.status = "failed"
        task.completed_at = datetime.now()
        
        # Broadcast error
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "type": "error",
            "status": "failed",
            "error": str(e),
            "message": f"Crawling failed: {str(e)}"
        }))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)