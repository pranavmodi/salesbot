#!/usr/bin/env python3
"""
Deep Company Research - Legacy Entry Point

This file maintains backward compatibility for the original deep_research_companies.py
while using the new modular architecture.

The code has been refactored into:
- database_service.py: Database operations
- ai_research_service.py: OpenAI API interactions
- report_generator.py: Markdown report generation
- company_researcher.py: Main orchestrator
- cli.py: Command line interface

For direct usage, import from the new modules:
    from deepresearch import CompanyResearcher, DatabaseService, AIResearchService
"""

from .cli import main

if __name__ == "__main__":
    main() 