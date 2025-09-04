from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
from typing import List, Optional
import json

class LeadgenCompany(Base):
    __tablename__ = "leadgen_companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True, unique=False, index=True)
    industry = Column(String(255), nullable=True, index=True)
    employee_count = Column(Integer, nullable=True, index=True)
    location = Column(String(255), nullable=True)
    founded_year = Column(Integer, nullable=True)
    technology_stack = Column(JSON, nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    source = Column(String(100), nullable=False, default="unknown", index=True)
    
    # Metadata fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # ATS scraping status
    ats_scraped = Column(Boolean, default=False, nullable=False)
    ats_scraped_at = Column(DateTime, nullable=True)
    last_scrape_status = Column(String(50), nullable=True)  # 'success', 'failed', 'in_progress'
    
    # Lead scoring fields
    support_roles_count = Column(Integer, default=0, nullable=False)
    sales_roles_count = Column(Integer, default=0, nullable=False)
    ai_roles_count = Column(Integer, default=0, nullable=False)
    lead_score = Column(Integer, default=0, nullable=False)
    is_qualified_lead = Column(Boolean, default=False, nullable=False)
    
    # Advanced lead scoring fields
    support_intensity_score = Column(Integer, default=0, nullable=False)
    digital_presence_score = Column(Integer, default=0, nullable=False)
    growth_signals_score = Column(Integer, default=0, nullable=False)
    implementation_feasibility_score = Column(Integer, default=0, nullable=False)
    lead_scoring_data = Column(JSON, nullable=True)  # Detailed signal data
    lead_scored_at = Column(DateTime, nullable=True)
    
    # Tenant creation fields
    tenant_id = Column(String(255), nullable=True)  # UUID from prodbot API
    tenant_created_at = Column(DateTime, nullable=True)
    
    # Tenant association for multi-tenancy
    salesbot_tenant_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    job_postings = relationship("LeadgenJobPosting", back_populates="company", cascade="all, delete-orphan")
    scraping_logs = relationship("LeadgenScrapingLog", back_populates="company", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert company to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'domain': self.domain,
            'industry': self.industry,
            'employee_count': self.employee_count,
            'location': self.location,
            'founded_year': self.founded_year,
            'technology_stack': self.technology_stack or [],
            'linkedin_url': self.linkedin_url,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'ats_scraped': self.ats_scraped,
            'ats_scraped_at': self.ats_scraped_at.isoformat() if self.ats_scraped_at else None,
            'last_scrape_status': self.last_scrape_status,
            'support_roles_count': self.support_roles_count,
            'sales_roles_count': self.sales_roles_count,
            'ai_roles_count': self.ai_roles_count,
            'lead_score': self.lead_score,
            'is_qualified_lead': self.is_qualified_lead,
            'support_intensity_score': self.support_intensity_score,
            'digital_presence_score': self.digital_presence_score,
            'growth_signals_score': self.growth_signals_score,
            'implementation_feasibility_score': self.implementation_feasibility_score,
            'lead_scoring_data': self.lead_scoring_data,
            'lead_scored_at': self.lead_scored_at.isoformat() if self.lead_scored_at else None,
            'tenant_id': self.tenant_id,
            'tenant_created_at': self.tenant_created_at.isoformat() if self.tenant_created_at else None,
            'salesbot_tenant_id': self.salesbot_tenant_id
        }

class LeadgenJobPosting(Base):
    __tablename__ = "leadgen_job_postings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("leadgen_companies.id"), nullable=False)
    external_id = Column(String(255), nullable=True, index=True)  # ATS-specific job ID
    
    title = Column(String(500), nullable=False)
    department = Column(String(255), nullable=True, index=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    job_url = Column(String(1000), nullable=True)
    
    # Job classification
    role_category = Column(String(100), nullable=True, index=True)  # 'support', 'sales', 'ai', 'other'
    seniority_level = Column(String(100), nullable=True)  # 'junior', 'mid', 'senior', 'lead', 'manager'
    
    # ATS information
    ats_source = Column(String(100), nullable=False, index=True)  # 'greenhouse', 'lever', 'workday', etc.
    posted_date = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Tenant association for multi-tenancy
    salesbot_tenant_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    company = relationship("LeadgenCompany", back_populates="job_postings")
    
    def to_dict(self):
        """Convert job posting to dictionary"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'external_id': self.external_id,
            'title': self.title,
            'department': self.department,
            'location': self.location,
            'description': self.description,
            'requirements': self.requirements,
            'job_url': self.job_url,
            'role_category': self.role_category,
            'seniority_level': self.seniority_level,
            'ats_source': self.ats_source,
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'salesbot_tenant_id': self.salesbot_tenant_id
        }

class LeadgenScrapingLog(Base):
    __tablename__ = "leadgen_scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("leadgen_companies.id"), nullable=False)
    task_id = Column(String(255), nullable=True, index=True)  # For tracking scraping tasks
    
    ats_source = Column(String(100), nullable=False)  # 'greenhouse', 'lever', etc.
    status = Column(String(50), nullable=False, index=True)  # 'started', 'completed', 'failed'
    jobs_found = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Additional metadata
    scraping_metadata = Column(JSON, nullable=True)  # Store additional scraping details
    
    # Tenant association for multi-tenancy
    salesbot_tenant_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    company = relationship("LeadgenCompany", back_populates="scraping_logs")
    
    def to_dict(self):
        """Convert scraping log to dictionary"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'task_id': self.task_id,
            'ats_source': self.ats_source,
            'status': self.status,
            'jobs_found': self.jobs_found,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'scraping_metadata': self.scraping_metadata,
            'salesbot_tenant_id': self.salesbot_tenant_id
        }

class LeadgenSeedingSession(Base):
    __tablename__ = "leadgen_seeding_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    
    source = Column(String(100), nullable=False)  # 'apollo', 'yc_sample', 'csv_import'
    status = Column(String(50), nullable=False, default='in_progress')  # 'in_progress', 'completed', 'failed'
    
    companies_found = Column(Integer, default=0, nullable=False)
    companies_imported = Column(Integer, default=0, nullable=False)
    
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Configuration used
    config = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Tenant association for multi-tenancy
    salesbot_tenant_id = Column(String(255), nullable=True, index=True)
    
    def to_dict(self):
        """Convert seeding session to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'source': self.source,
            'status': self.status,
            'companies_found': self.companies_found,
            'companies_imported': self.companies_imported,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'config': self.config,
            'error_message': self.error_message,
            'salesbot_tenant_id': self.salesbot_tenant_id
        }