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
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @staticmethod
    def _get_db_engine():
        """Get database engine from environment."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            current_app.logger.error("DATABASE_URL not configured.")
            return None
        try:
            return create_engine(database_url)
        except Exception as e:
            current_app.logger.error(f"Error creating database engine: {e}")
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
                    SELECT id, company_name, website_url, company_research, created_at, updated_at
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
                    SELECT id, company_name, website_url, company_research, created_at, updated_at
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
                    SELECT id, company_name, website_url, company_research, created_at, updated_at
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
                    SELECT id, company_name, website_url, company_research, created_at, updated_at
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

    def to_dict(self) -> Dict:
        """Convert company to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'website_url': self.website_url,
            'company_research': self.company_research,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at) if self.updated_at else None
        } 