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
from typing import Dict, Tuple
from .report_renderer import ReportRenderer

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Handles markdown report generation and file operations."""
    
    def __init__(self, reports_base_dir: str = None):
        if reports_base_dir is None:
            self.reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        else:
            self.reports_dir = reports_base_dir
        
        # Initialize report renderer
        self.renderer = ReportRenderer()
        
        # Create reports directory if it doesn't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        logger.info(f"ReportGenerator initialized with HTML/PDF rendering")

    def generate_strategic_report(self, company_name: str, research_content: str, strategic_content: str) -> Dict[str, str]:
        """Generate McKinsey-style client-facing strategic report in HTML and PDF formats."""
        logger.info(f"Generating strategic report for: {company_name}")
        
        try:
            # Generate HTML and PDF using the renderer
            html_content, pdf_bytes = self.renderer.render_strategic_report(company_name, strategic_content)
            
            # Convert PDF to base64 for storage/transmission
            pdf_base64 = self.renderer.get_pdf_base64(pdf_bytes)
            
            logger.info(f"Successfully generated strategic report for: {company_name}")
            
            return {
                'html_report': html_content,
                'pdf_report_base64': pdf_base64,
                'pdf_bytes': pdf_bytes  # For immediate use
            }
            
        except Exception as e:
            logger.error(f"Error generating strategic report for {company_name}: {e}")
            raise

    # Legacy method kept for backward compatibility - will be removed
    def generate_markdown_report(self, company_name: str, research_content: str, strategic_content: str) -> str:
        """Legacy method - use generate_strategic_report instead."""
        logger.warning("generate_markdown_report is deprecated, use generate_strategic_report")
        result = self.generate_strategic_report(company_name, research_content, strategic_content)
        # Return HTML content as fallback
        return result['html_report']

    def write_markdown_report(self, company_name: str, company_research: str, strategic_analysis: str) -> bool:
        """Write combined research and strategic analysis to markdown file."""
        logger.info(f"Writing markdown report to file for: {company_name}")
        
        # Generate filename using sanitized company name
        safe_company_name = self._sanitize_filename(company_name)
        filename = f"{safe_company_name}_analysis.md"
        filepath = os.path.join(self.reports_dir, filename)
        
        # Get the markdown content
        full_report = self.generate_markdown_report(company_name, company_research, strategic_analysis)
        
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

    def write_report_file(self, company_name: str, markdown_content: str) -> bool:
        """Write markdown report directly to file."""
        try:
            os.makedirs(self.reports_dir, exist_ok=True)
            
            # Clean company name for filename
            safe_name = self._sanitize_filename(company_name)
            report_filename = f"{safe_name}_research_report.md"
            report_path = os.path.join(self.reports_dir, report_filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Report file written: {report_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing report file for {company_name}: {e}")
            return False

    def _sanitize_filename(self, company_name: str) -> str:
        """Sanitize company name for use in filenames."""
        safe_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return safe_name.replace(' ', '_').lower() 