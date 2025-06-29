#!/usr/bin/env python3
"""
Report Generator

Handles markdown report generation and file operations for:
- Creating comprehensive company analysis reports
- Managing report directory structure
- File system operations for report storage
"""

import os
import time
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Handles markdown report generation and file operations."""
    
    def __init__(self, reports_base_dir: str = None):
        if reports_base_dir is None:
            self.reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        else:
            self.reports_dir = reports_base_dir
        
        # Create reports directory if it doesn't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        logger.info(f"ReportGenerator initialized with reports directory: {self.reports_dir}")

    def write_markdown_report(self, company_name: str, research_content: str, strategic_content: str) -> bool:
        """Write combined research and strategic analysis to markdown file."""
        logger.info(f"Writing markdown report for: {company_name}")
        
        # Generate filename (company name with safe characters)
        safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_company_name = safe_company_name.replace(' ', '_').lower()
        filename = f"{safe_company_name}_analysis.md"
        filepath = os.path.join(self.reports_dir, filename)
        
        # Combine research and strategic analysis
        full_report = f"""# Deep Research Analysis: {company_name}

*Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*

---

## Company Research Analysis

{research_content}

---

{strategic_content}

---

*This analysis was generated using AI-powered research and strategic analysis tools. All recommendations should be validated with current market data and company-specific context.*
"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_report)
            
            logger.info(f"Successfully wrote report to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing markdown report for {company_name}: {e}")
            return False

    def get_reports_directory(self) -> str:
        """Get the path to the reports directory."""
        return self.reports_dir

    def list_reports(self) -> list:
        """List all existing report files in the reports directory."""
        try:
            if os.path.exists(self.reports_dir):
                return [f for f in os.listdir(self.reports_dir) if f.endswith('.md')]
            return []
        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            return []

    def delete_report(self, company_name: str) -> bool:
        """Delete a specific company's report file."""
        safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_company_name = safe_company_name.replace(' ', '_').lower()
        filename = f"{safe_company_name}_analysis.md"
        filepath = os.path.join(self.reports_dir, filename)
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Successfully deleted report: {filepath}")
                return True
            else:
                logger.warning(f"Report file not found: {filepath}")
                return False
        except Exception as e:
            logger.error(f"Error deleting report for {company_name}: {e}")
            return False 