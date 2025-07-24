#!/usr/bin/env python3
"""
Report Renderer

Handles HTML/PDF report generation using Jinja2 templates and WeasyPrint:
- Renders strategic reports to styled HTML
- Generates PDF versions for download
- Processes strategic content for better formatting
"""

import os
import base64
import logging
import re
from typing import Dict, Tuple, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Try to import WeasyPrint, fallback to HTML-only mode if dependencies missing
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WeasyPrint not available: {e}. PDF generation will be disabled.")
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
    FontConfiguration = None

logger = logging.getLogger(__name__)

class ReportRenderer:
    """Handles HTML/PDF report rendering using Jinja2 and WeasyPrint."""
    
    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        else:
            self.templates_dir = templates_dir
            
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True
        )
        
        # Initialize WeasyPrint font configuration if available
        if WEASYPRINT_AVAILABLE:
            self.font_config = FontConfiguration()
        else:
            self.font_config = None
        
        logger.info(f"ReportRenderer initialized with templates directory: {self.templates_dir}")

    def render_strategic_report(self, company_name: str, strategic_content: str) -> Tuple[str, bytes]:
        """
        Render strategic report to both HTML and PDF formats.
        
        Args:
            company_name: Name of the company
            strategic_content: Strategic analysis content (markdown format)
            
        Returns:
            Tuple of (html_content, pdf_bytes)
        """
        logger.info(f"Rendering strategic report for: {company_name}")
        
        try:
            # Process strategic content for better HTML formatting
            formatted_content = self._format_strategic_content_for_html(strategic_content)
            
            # Prepare template variables
            template_vars = {
                'company_name': company_name,
                'strategic_content': formatted_content,
                'generation_date': datetime.now().strftime('%B %d, %Y')
            }
            
            # Render HTML
            html_content = self._render_html_template(template_vars)
            
            # Generate PDF if WeasyPrint is available
            if WEASYPRINT_AVAILABLE and self.font_config:
                pdf_bytes = self._generate_pdf_from_html(html_content)
                logger.info(f"Successfully rendered report for {company_name} (HTML: {len(html_content)} chars, PDF: {len(pdf_bytes)} bytes)")
            else:
                pdf_bytes = b''  # Empty bytes for PDF
                logger.info(f"Successfully rendered HTML report for {company_name} (HTML: {len(html_content)} chars, PDF disabled)")
            
            return html_content, pdf_bytes
            
        except Exception as e:
            logger.error(f"Error rendering report for {company_name}: {e}")
            raise

    def _render_html_template(self, template_vars: Dict) -> str:
        """Render HTML using Jinja2 template."""
        try:
            template = self.jinja_env.get_template('strategic_report.html')
            html_content = template.render(**template_vars)
            return html_content
        except Exception as e:
            logger.error(f"Error rendering HTML template: {e}")
            raise

    def _generate_pdf_from_html(self, html_content: str) -> bytes:
        """Generate PDF from HTML content using WeasyPrint."""
        if not WEASYPRINT_AVAILABLE:
            logger.warning("WeasyPrint not available, cannot generate PDF")
            return b''
            
        try:
            # Create HTML document
            html_doc = HTML(string=html_content)
            
            # Generate PDF with proper font configuration
            pdf_bytes = html_doc.write_pdf(font_config=self.font_config)
            
            return pdf_bytes
        except Exception as e:
            logger.error(f"Error generating PDF from HTML: {e}")
            raise

    def _format_strategic_content_for_html(self, content: str) -> str:
        """Format strategic content from markdown to HTML-friendly format."""
        formatted = content
        
        # Convert markdown headers to HTML
        formatted = re.sub(r'^### (.*)', r'<div class="strategic-imperative"><div class="imperative-title">\1</div>', formatted, flags=re.MULTILINE)
        
        # Format context sections
        formatted = re.sub(
            r'\*\*📋 Context:\*\*(.*?)(?=\*\*🚀|$)', 
            r'<div class="section-label"><span class="emoji">📋</span> Context:</div><div class="section-content">\1</div>', 
            formatted, 
            flags=re.DOTALL
        )
        
        # Format AI Agent Opportunity sections
        formatted = re.sub(
            r'\*\*🚀 AI Agent Opportunity:\*\*(.*?)(?=\*\*💰|$)', 
            r'<div class="section-label"><span class="emoji">🚀</span> AI Agent Opportunity:</div><div class="section-content">\1</div>', 
            formatted, 
            flags=re.DOTALL
        )
        
        # Format Expected Impact sections
        formatted = re.sub(
            r'\*\*💰 Expected Impact:\*\*(.*?)(?=</div>|###|##|$)', 
            r'<div class="section-label"><span class="emoji">💰</span> Expected Impact:</div><div class="section-content">\1</div></div>', 
            formatted, 
            flags=re.DOTALL
        )
        
        # Format main sections
        formatted = re.sub(r'^## (🤖 AI Agent Recommendations)', r'<h2>\1</h2>', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^## (📈 Expected Business Impact)', r'<h2>\1</h2>', formatted, flags=re.MULTILINE)
        
        # Format priority recommendations
        formatted = re.sub(
            r'\*\*🥇 Priority 1:\*\*(.*?)(?=- \*\*Use Case|\*\*🥈|$)', 
            r'<div class="recommendations-grid"><div class="priority-card"><div class="priority-title"><span class="emoji">🥇</span> Priority 1:\1</div>', 
            formatted, 
            flags=re.DOTALL
        )
        
        formatted = re.sub(
            r'🥈 \*\*Priority 2:\*\*(.*?)(?=- \*\*Use Case|$)', 
            r'</div><div class="priority-card"><div class="priority-title"><span class="emoji">🥈</span> Priority 2:\1</div>', 
            formatted, 
            flags=re.DOTALL
        )
        
        # Format use cases and business impact within priority cards
        formatted = re.sub(r'- \*\*Use Case:\*\*(.*?)(?=- \*\*Business Impact|$)', r'<div><strong>Use Case:</strong>\1</div>', formatted, flags=re.DOTALL)
        formatted = re.sub(r'- \*\*Business Impact:\*\*(.*?)(?=</div>|$)', r'<div><strong>Business Impact:</strong>\1</div></div>', formatted, flags=re.DOTALL)
        
        # Close recommendations grid
        if '🥈' in formatted:
            formatted += '</div>'
        
        # Format impact lists
        formatted = re.sub(r'^- (.*)', r'<ul class="impact-list"><li>\1</li></ul>', formatted, flags=re.MULTILINE)
        
        # Merge consecutive list items
        formatted = re.sub(r'</ul>\s*<ul class="impact-list">', '', formatted)
        
        # Clean up extra newlines and whitespace
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        formatted = re.sub(r'<div class="section-content">\s*\n\s*', '<div class="section-content">', formatted)
        
        return formatted.strip()

    def get_pdf_base64(self, pdf_bytes: bytes) -> str:
        """Convert PDF bytes to base64 string for API payload."""
        return base64.b64encode(pdf_bytes).decode('utf-8')

    def save_reports_to_files(self, company_name: str, html_content: str, pdf_bytes: bytes, output_dir: str = None) -> Dict[str, str]:
        """
        Save HTML and PDF reports to files (optional, for local storage).
        
        Returns:
            Dictionary with file paths
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "reports")
        
        # Create company-specific directory
        company_dir = os.path.join(output_dir, self._sanitize_filename(company_name))
        os.makedirs(company_dir, exist_ok=True)
        
        # Save HTML file
        html_path = os.path.join(company_dir, "report.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Save PDF file
        pdf_path = os.path.join(company_dir, "report.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        logger.info(f"Saved reports for {company_name} to {company_dir}")
        
        return {
            'html_path': html_path,
            'pdf_path': pdf_path,
            'company_dir': company_dir
        }

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize company name for use as filename."""
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Replace spaces with underscores
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        return sanitized.lower()