from datetime import datetime
from typing import List, Dict, Optional
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

class Company:
    """Company model for managing company data from PostgreSQL database."""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.company_name = data.get('company_name', '')
        self.website_url = data.get('website_url', '')
        self.company_research = data.get('company_research', '')
        self.markdown_report = data.get('markdown_report', '')
        self.html_report = data.get('html_report', '')
        self.pdf_report_base64 = data.get('pdf_report_base64', '')
        self.strategic_imperatives = data.get('strategic_imperatives', '')
        self.agent_recommendations = data.get('agent_recommendations', '')
        
        # Research step tracking fields
        self.research_status = data.get('research_status', 'pending')  # pending, in_progress, completed, failed
        self.research_step_1_basic = data.get('research_step_1_basic', '')
        self.research_step_2_strategic = data.get('research_step_2_strategic', '')
        self.research_step_3_report = data.get('research_step_3_report', '')
        self.research_started_at = data.get('research_started_at')
        self.research_completed_at = data.get('research_completed_at')
        self.research_error = data.get('research_error', '')
        
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @staticmethod
    def _get_db_engine():
        """Get shared database engine."""
        try:
            from app.database import get_shared_engine
            return get_shared_engine()
        except Exception as e:
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error getting shared database engine: {e}")
            else:
                print(f"Error getting shared database engine: {e}")
            return None

    @classmethod
    def load_all(cls) -> List['Company']:
        """Load all companies from PostgreSQL database."""
        companies = []
        engine = cls._get_db_engine()
        if not engine:
            return companies
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, 
                           COALESCE(company_research, '') as company_research, 
                           COALESCE(markdown_report, '') as markdown_report,
                           COALESCE(html_report, '') as html_report, 
                           COALESCE(pdf_report_base64, '') as pdf_report_base64, 
                           COALESCE(strategic_imperatives, '') as strategic_imperatives, 
                           COALESCE(agent_recommendations, '') as agent_recommendations,
                           COALESCE(research_status, 'pending') as research_status, 
                           COALESCE(research_step_1_basic, '') as research_step_1_basic, 
                           COALESCE(research_step_2_strategic, '') as research_step_2_strategic, 
                           COALESCE(research_step_3_report, '') as research_step_3_report, 
                           research_started_at, research_completed_at, 
                           COALESCE(research_error, '') as research_error, 
                           COALESCE(created_at, CURRENT_TIMESTAMP) as created_at, 
                           COALESCE(updated_at, CURRENT_TIMESTAMP) as updated_at
                    FROM companies 
                    ORDER BY created_at DESC
                """))
                
                for row in result:
                    company_data = dict(row._mapping)
                    companies.append(cls(company_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error loading companies from database: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error loading companies: {e}")
            
        return companies

    @classmethod
    def get_paginated(cls, page: int = 1, per_page: int = 10) -> Dict:
        """Get paginated companies from PostgreSQL database."""
        companies = []
        total = 0
        engine = cls._get_db_engine()
        
        if not engine:
            return {
                'companies': [],
                'current_page': page,
                'total_pages': 0,
                'per_page': per_page,
                'total_companies': 0
            }
            
        try:
            with engine.connect() as conn:
                # Get total count
                count_result = conn.execute(text("SELECT COUNT(*) FROM companies"))
                total = count_result.scalar()
                
                # Get paginated results
                offset = (page - 1) * per_page
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, 
                           COALESCE(company_research, '') as company_research, 
                           COALESCE(markdown_report, '') as markdown_report,
                           COALESCE(html_report, '') as html_report, 
                           COALESCE(pdf_report_base64, '') as pdf_report_base64, 
                           COALESCE(strategic_imperatives, '') as strategic_imperatives, 
                           COALESCE(agent_recommendations, '') as agent_recommendations,
                           COALESCE(research_status, 'pending') as research_status, 
                           COALESCE(research_step_1_basic, '') as research_step_1_basic, 
                           COALESCE(research_step_2_strategic, '') as research_step_2_strategic, 
                           COALESCE(research_step_3_report, '') as research_step_3_report, 
                           research_started_at, research_completed_at, 
                           COALESCE(research_error, '') as research_error, 
                           COALESCE(created_at, CURRENT_TIMESTAMP) as created_at, 
                           COALESCE(updated_at, CURRENT_TIMESTAMP) as updated_at
                    FROM companies 
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """), {"limit": per_page, "offset": offset})
                
                for row in result:
                    company_data = dict(row._mapping)
                    companies.append(cls(company_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting paginated companies: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting paginated companies: {e}")
        
        total_pages = (total + per_page - 1) // per_page
        
        return {
            'companies': companies,
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_companies': total
        }

    @classmethod
    def search(cls, query: str) -> List['Company']:
        """Search companies by name, website, or research content in PostgreSQL database."""
        companies = []
        engine = cls._get_db_engine()
        if not engine:
            return companies
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, company_research, markdown_report,
                           html_report, pdf_report_base64, strategic_imperatives, agent_recommendations,
                           research_status, research_step_1_basic, research_step_2_strategic, 
                           research_step_3_report, research_started_at, research_completed_at, 
                           research_error, created_at, updated_at
                    FROM companies 
                    WHERE company_name ILIKE :search OR website_url ILIKE :search 
                       OR company_research ILIKE :search
                    ORDER BY created_at DESC
                    LIMIT 50
                """), {"search": f"%{query}%"})
                
                for row in result:
                    company_data = dict(row._mapping)
                    companies.append(cls(company_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error searching companies: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error searching companies: {e}")
            
        return companies

    @classmethod
    def get_by_id(cls, company_id: int) -> Optional['Company']:
        """Get a company by ID."""
        engine = cls._get_db_engine()
        if not engine:
            return None
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, company_research, markdown_report,
                           html_report, pdf_report_base64, strategic_imperatives, agent_recommendations,
                           research_status, research_step_1_basic, research_step_2_strategic, 
                           research_step_3_report, research_started_at, research_completed_at, 
                           research_error, created_at, updated_at
                    FROM companies 
                    WHERE id = :id
                """), {"id": company_id})
                
                row = result.fetchone()
                if row:
                    company_data = dict(row._mapping)
                    return cls(company_data)
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting company by ID: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting company by ID: {e}")
            
        return None

    @classmethod
    def get_companies_by_name(cls, company_name: str) -> List['Company']:
        """Get companies by name (case-insensitive search)."""
        companies = []
        engine = cls._get_db_engine()
        if not engine:
            return companies
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, company_research, markdown_report,
                           html_report, pdf_report_base64, strategic_imperatives, agent_recommendations,
                           research_status, research_step_1_basic, research_step_2_strategic, 
                           research_step_3_report, research_started_at, research_completed_at, 
                           research_error, created_at, updated_at
                    FROM companies 
                    WHERE LOWER(company_name) = LOWER(:company_name)
                    ORDER BY created_at DESC
                """), {"company_name": company_name})
                
                for row in result:
                    company_data = dict(row._mapping)
                    companies.append(cls(company_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting companies by name: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting companies by name: {e}")
            
        return companies

    @classmethod
    def get_companies_with_reports(cls) -> List[Dict]:
        """Get all companies that have markdown reports for public consumption."""
        companies = []
        engine = cls._get_db_engine()
        if not engine:
            return companies
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, created_at, updated_at
                    FROM companies 
                    WHERE markdown_report IS NOT NULL 
                      AND markdown_report != ''
                    ORDER BY updated_at DESC
                """))
                
                for row in result:
                    companies.append({
                        'id': row.id,
                        'company_name': row.company_name,
                        'website_url': row.website_url,
                        'created_at': row.created_at,
                        'updated_at': row.updated_at
                    })
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting companies with reports: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting companies with reports: {e}")
            
        return companies

    @classmethod
    def save(cls, company_data: Dict) -> bool:
        """Save a new company to the database."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to save company: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    insert_query = text("""
                        INSERT INTO companies (company_name, website_url, company_research) 
                        VALUES (:company_name, :website_url, :company_research)
                    """)
                    conn.execute(insert_query, {
                        'company_name': company_data['company_name'],
                        'website_url': company_data['website_url'],
                        'company_research': company_data['company_research']
                    })
            current_app.logger.info(f"Successfully saved company: {company_data['company_name']}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error saving company: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error saving company: {e}")
            return False

    @classmethod
    def update(cls, company_id: int, company_data: Dict) -> bool:
        """Update an existing company in the database."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to update company: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    update_query = text("""
                        UPDATE companies 
                        SET company_name = :company_name, 
                            website_url = :website_url, 
                            company_research = :company_research,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    result = conn.execute(update_query, {
                        'id': company_id,
                        'company_name': company_data['company_name'],
                        'website_url': company_data['website_url'],
                        'company_research': company_data['company_research']
                    })
                    
                    if result.rowcount == 0:
                        current_app.logger.warning(f"No company found with ID: {company_id}")
                        return False
                        
            current_app.logger.info(f"Successfully updated company: {company_data['company_name']}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating company: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error updating company: {e}")
            return False

    @classmethod
    def delete(cls, company_id: int) -> bool:
        """Delete a company from the database."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to delete company: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    delete_query = text("DELETE FROM companies WHERE id = :id")
                    result = conn.execute(delete_query, {"id": company_id})
                    
                    if result.rowcount == 0:
                        current_app.logger.warning(f"No company found with ID: {company_id}")
                        return False
                        
            current_app.logger.info(f"Successfully deleted company with ID: {company_id}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error deleting company: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error deleting company: {e}")
            return False

    @classmethod
    def update_research_status(cls, company_id: int, status: str, error: str = None) -> bool:
        """Update research status for a company."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to update research status: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    if status == 'in_progress':
                        update_query = text("""
                            UPDATE companies 
                            SET research_status = :status, 
                                research_started_at = CURRENT_TIMESTAMP,
                                research_error = NULL,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        conn.execute(update_query, {'id': company_id, 'status': status})
                    elif status == 'completed':
                        update_query = text("""
                            UPDATE companies 
                            SET research_status = :status, 
                                research_completed_at = CURRENT_TIMESTAMP,
                                research_error = NULL,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        conn.execute(update_query, {'id': company_id, 'status': status})
                    elif status == 'failed':
                        update_query = text("""
                            UPDATE companies 
                            SET research_status = :status, 
                                research_error = :error,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        conn.execute(update_query, {'id': company_id, 'status': status, 'error': error or ''})
                    else:
                        update_query = text("""
                            UPDATE companies 
                            SET research_status = :status, 
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        conn.execute(update_query, {'id': company_id, 'status': status})
                        
            current_app.logger.info(f"Successfully updated research status to {status} for company ID: {company_id}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating research status: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error updating research status: {e}")
            return False

    @classmethod
    def update_research_step(cls, company_id: int, step: int, content: str) -> bool:
        """Update a specific research step for a company."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to update research step: Database engine not available.")
            return False

        step_column_map = {
            1: 'research_step_1_basic',
            2: 'research_step_2_strategic', 
            3: 'research_step_3_report'
        }
        
        if step not in step_column_map:
            current_app.logger.error(f"Invalid research step: {step}")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    column_name = step_column_map[step]
                    update_query = text(f"""
                        UPDATE companies 
                        SET {column_name} = :content,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    result = conn.execute(update_query, {'id': company_id, 'content': content})
                    
                    if result.rowcount == 0:
                        current_app.logger.warning(f"No company found with ID: {company_id}")
                        return False
                        
            current_app.logger.info(f"Successfully updated research step {step} for company ID: {company_id}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating research step: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error updating research step: {e}")
            return False

    @classmethod
    def update_full_research(cls, company_id: int, basic_research: str, strategic_analysis: str, markdown_report: str) -> bool:
        """Update all research steps and markdown report for a company."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to update full research: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    update_query = text("""
                        UPDATE companies 
                        SET research_step_1_basic = :basic_research,
                            research_step_2_strategic = :strategic_analysis,
                            research_step_3_report = :markdown_report,
                            company_research = :basic_research,
                            markdown_report = :markdown_report,
                            research_status = 'completed',
                            research_completed_at = CURRENT_TIMESTAMP,
                            research_error = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    result = conn.execute(update_query, {
                        'id': company_id,
                        'basic_research': basic_research,
                        'strategic_analysis': strategic_analysis,
                        'markdown_report': markdown_report
                    })
                    
                    if result.rowcount == 0:
                        current_app.logger.warning(f"No company found with ID: {company_id}")
                        return False
                        
            current_app.logger.info(f"Successfully updated full research for company ID: {company_id}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating full research: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error updating full research: {e}")
            return False

    def to_dict(self) -> Dict:
        """Convert company to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'website_url': self.website_url,
            'company_research': self.company_research,
            'markdown_report': self.markdown_report,
            'html_report': self.html_report,
            'pdf_report_base64': self.pdf_report_base64,
            'strategic_imperatives': self.strategic_imperatives,
            'agent_recommendations': self.agent_recommendations,
            'research_status': self.research_status,
            'research_step_1_basic': self.research_step_1_basic,
            'research_step_2_strategic': self.research_step_2_strategic,
            'research_step_3_report': self.research_step_3_report,
            'research_started_at': self.research_started_at.isoformat() if isinstance(self.research_started_at, datetime) else str(self.research_started_at) if self.research_started_at else None,
            'research_completed_at': self.research_completed_at.isoformat() if isinstance(self.research_completed_at, datetime) else str(self.research_completed_at) if self.research_completed_at else None,
            'research_error': self.research_error,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at) if self.updated_at else None
        }

    @classmethod
    def search_by_name(cls, company_name: str) -> List[Dict]:
        """Search companies by name for click tracking."""
        engine = cls._get_db_engine()
        if not engine:
            return []
        
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT id, company_name, website_url, company_research, markdown_report,
                           html_report, pdf_report_base64, strategic_imperatives, agent_recommendations
                    FROM companies 
                    WHERE LOWER(company_name) LIKE LOWER(:company_name)
                    ORDER BY company_name
                """)
                
                result = conn.execute(query, {'company_name': f'%{company_name}%'})
                
                companies = []
                for row in result:
                    companies.append({
                        'id': row.id,
                        'company_name': row.company_name,
                        'website_url': row.website_url,
                        'company_research': row.company_research,
                        'markdown_report': row.markdown_report,
                        'html_report': row.html_report,
                        'pdf_report_base64': row.pdf_report_base64,
                        'strategic_imperatives': row.strategic_imperatives,
                        'agent_recommendations': row.agent_recommendations
                    })
                
                return companies
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error searching companies by name: {e}")
            return []
        except Exception as e:
            current_app.logger.error(f"Unexpected error searching companies by name: {e}")
            return []