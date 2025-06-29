"""
Deep Research Package

A modular company research system that uses AI to analyze companies
and generate strategic recommendations for sales outreach.

Modules:
- database_service: Database operations and company data management
- ai_research_service: OpenAI-powered company research and analysis  
- report_generator: Markdown report generation and file operations
- company_researcher: Main orchestrator coordinating all services
- cli: Command line interface for the research workflow
"""

from .database_service import DatabaseService
from .ai_research_service import AIResearchService
from .report_generator import ReportGenerator
from .company_researcher import CompanyResearcher

__version__ = "1.0.0"
__all__ = [
    "DatabaseService",
    "AIResearchService", 
    "ReportGenerator",
    "CompanyResearcher"
] 