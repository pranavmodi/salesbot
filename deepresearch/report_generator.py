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

    def generate_markdown_report(self, company_name: str, research_content: str, strategic_content: str) -> str:
        """Generate McKinsey-style client-facing strategic report."""
        logger.info(f"Generating client-facing strategic report for: {company_name}")
        
        # Create polished client report with better formatting
        formatted_content = self._format_strategic_content(strategic_content)
        
        full_report = f"""# Strategic Analysis: {company_name}

## Executive Summary

Based on comprehensive market analysis and competitive intelligence, we have identified key strategic imperatives and AI agent opportunities that can accelerate **{company_name}'s** growth and operational excellence.

---

{formatted_content}

---

*Strategic analysis prepared by [Possible Minds](https://possibleminds.in)* | *Generated on {time.strftime('%B %d, %Y')}*"""
        
        logger.info(f"Successfully generated markdown report for: {company_name}")
        return full_report

    def _format_strategic_content(self, content: str) -> str:
        """Format strategic content for better readability."""
        # Add proper spacing and visual hierarchy
        formatted = content
        
        # Add spacing after strategic imperatives headers
        formatted = formatted.replace('### Strategic Imperative', '\n### 🎯 Strategic Imperative')
        
        # Format AI Agent Recommendations section
        formatted = formatted.replace('## AI Agent Recommendations', '\n## 🤖 AI Agent Recommendations')
        
        # Format Expected Business Impact section  
        formatted = formatted.replace('## Expected Business Impact', '\n## 📈 Expected Business Impact')
        
        # Add better formatting for context/opportunity/impact sections
        formatted = formatted.replace('**Context:**', '\n**📋 Context:**')
        formatted = formatted.replace('**AI Agent Opportunity:**', '\n**🚀 AI Agent Opportunity:**')
        formatted = formatted.replace('**Expected Impact:**', '\n**💰 Expected Impact:**')
        
        # Add spacing for priority items
        formatted = formatted.replace('**Priority 1:**', '\n**🥇 Priority 1:**')
        formatted = formatted.replace('**Priority 2:**', '\n🥈 **Priority 2:**')
        
        # Clean up extra newlines and ensure proper spacing
        import re
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        return formatted.strip()

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