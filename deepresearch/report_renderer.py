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

# WeasyPrint will be imported dynamically when needed
WEASYPRINT_AVAILABLE = None  # Will be set on first use
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
        
        # Font configuration will be initialized when WeasyPrint is first used
        self.font_config = None
        
        logger.info(f"ReportRenderer initialized with templates directory: {self.templates_dir}")

    def _init_weasyprint(self) -> bool:
        """Initialize WeasyPrint on first use. Returns True if successful."""
        global WEASYPRINT_AVAILABLE, HTML, CSS, FontConfiguration
        
        if WEASYPRINT_AVAILABLE is not None:
            return WEASYPRINT_AVAILABLE
        
        try:
            from weasyprint import HTML as _HTML, CSS as _CSS
            from weasyprint.text.fonts import FontConfiguration as _FontConfiguration
            
            HTML = _HTML
            CSS = _CSS
            FontConfiguration = _FontConfiguration
            WEASYPRINT_AVAILABLE = True
            
            # Initialize font configuration
            self.font_config = FontConfiguration()
            
            logger.info("WeasyPrint initialized successfully")
            return True
            
        except Exception as e:
            logger.warning(f"WeasyPrint not available: {e}. PDF generation will be disabled.")
            WEASYPRINT_AVAILABLE = False
            return False

    def render_strategic_report(self, company_name: str, strategic_content: str, basic_research: str = None) -> Tuple[str, bytes]:
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
            # Generate company-specific executive summary with strategic imperatives
            executive_summary = None
            if basic_research and strategic_content:
                from .ai_research_service import AIResearchService
                ai_service = AIResearchService()
                executive_summary = ai_service.generate_executive_summary_with_imperatives(company_name, basic_research, strategic_content)
            
            # Process strategic content for better HTML formatting
            formatted_content = self._format_strategic_content_for_html(strategic_content)
            
            # Prepare template variables
            template_vars = {
                'company_name': company_name,
                'strategic_content': formatted_content,
                'executive_summary': executive_summary,
                'generation_date': datetime.now().strftime('%B %d, %Y')
            }
            
            # Render HTML
            html_content = self._render_html_template(template_vars)
            
            # Generate PDF if WeasyPrint is available
            if self._init_weasyprint():
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
        if not self._init_weasyprint():
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
        """Format strategic content from markdown to HTML-friendly format with structured output support."""
        formatted = content
        
        # Check if content appears to be from structured outputs (well-formatted already)
        if self._is_structured_output_format(content):
            # Content is already well-structured, apply minimal formatting
            formatted = self._format_structured_content(formatted)
        else:
            # Legacy content - use the original complex formatting logic
            formatted = self._format_legacy_content(formatted)
        
        return formatted.strip()

    def _is_structured_output_format(self, content: str) -> bool:
        """Detect if content is from structured outputs (well-formatted already)."""
        # Check for clean, consistent formatting patterns
        has_strategic_imperatives = "### Strategic Imperative 1:" in content and "### Strategic Imperative 2:" in content
        has_clean_sections = "**📋 Context:**" in content and "**🚀 AI Agent Opportunity:**" in content
        has_recommendations = "## 🤖 AI Agent Recommendations" in content
        
        return has_strategic_imperatives and has_clean_sections and has_recommendations

    def _format_structured_content(self, content: str) -> str:
        """Format content that's already well-structured from structured outputs."""
        formatted = content
        
        # Process each strategic imperative separately to ensure proper div closure
        imperative_sections = re.split(r'^(### Strategic Imperative \d+: .+)$', formatted, flags=re.MULTILINE)
        
        if len(imperative_sections) > 1:
            result_parts = [imperative_sections[0]]  # Keep any content before first imperative
            
            for i in range(1, len(imperative_sections), 2):
                if i + 1 < len(imperative_sections):
                    header = imperative_sections[i]
                    content_section = imperative_sections[i + 1]
                    
                    # Format the header
                    header_match = re.match(r'### Strategic Imperative (\d+): (.+)', header)
                    if header_match:
                        imperative_num = header_match.group(1)
                        imperative_title = header_match.group(2)
                        
                        # Start the strategic imperative container with anchor ID
                        imperative_id = f"imperative-{imperative_num}"
                        formatted_section = f'<div class="strategic-imperative" id="{imperative_id}"><div class="imperative-title">Strategic Imperative {imperative_num}: {imperative_title}</div>'
                        
                        # Format the content sections within this imperative
                        section_content = content_section
                        
                        # Format context sections
                        section_content = re.sub(
                            r'\*\*📋 Context:\*\* (.+?)(?=\*\*🚀|\n\n|$)',
                            r'<div class="section-label"><span class="emoji">📋</span> Context:</div><div class="section-content">\1</div>',
                            section_content,
                            flags=re.DOTALL
                        )
                        
                        # Format AI Agent Opportunity sections
                        section_content = re.sub(
                            r'\*\*🚀 AI Agent Opportunity:\*\*\n(.+?)(?=\*\*💰|$)',
                            r'<div class="section-label"><span class="emoji">🚀</span> AI Agent Opportunity:</div><div class="section-content">\1</div>',
                            section_content,
                            flags=re.DOTALL
                        )
                        
                        # Format Expected Impact sections
                        section_content = re.sub(
                            r'\*\*💰 Expected Impact:\*\* (.+?)(?=\n|$)',
                            r'<div class="section-label"><span class="emoji">💰</span> Expected Impact:</div><div class="section-content">\1</div>',
                            section_content,
                            flags=re.DOTALL
                        )
                        
                        # Close the strategic imperative container
                        formatted_section += section_content + '</div>'
                        result_parts.append(formatted_section)
            
            formatted = ''.join(result_parts)
        
        return formatted

    def _format_legacy_content(self, content: str) -> str:
        """Format legacy content using the original complex logic."""
        # First, split content by strategic imperatives to handle them separately
        imperative_sections = re.split(r'^### (.*?)$', content, flags=re.MULTILINE)
        
        if len(imperative_sections) > 1:
            # Process each strategic imperative section separately
            result_parts = [imperative_sections[0]]  # Keep any content before first ###
            
            for i in range(1, len(imperative_sections), 2):
                if i + 1 < len(imperative_sections):
                    title = imperative_sections[i]
                    content_section = imperative_sections[i + 1]
                    
                    # Extract imperative number from title if it matches the pattern
                    imperative_num = None
                    num_match = re.match(r'Strategic Imperative (\d+):', title)
                    if num_match:
                        imperative_num = int(num_match.group(1))
                    
                    # Format this individual imperative with number for anchor ID
                    formatted_section = self._format_single_imperative(title, content_section, imperative_num)
                    result_parts.append(formatted_section)
            
            formatted = ''.join(result_parts)
        else:
            # No strategic imperatives found, format as regular content
            formatted = self._format_regular_content(content)
        
        return formatted

    def _format_single_imperative(self, title: str, content: str, imperative_num: int = None) -> str:
        """Format a single strategic imperative with proper div nesting and anchor ID."""
        # Create the imperative container with anchor ID if number provided
        if imperative_num:
            imperative_id = f"imperative-{imperative_num}"
            result = f'<div class="strategic-imperative" id="{imperative_id}"><div class="imperative-title">{title.strip()}</div>'
        else:
            result = f'<div class="strategic-imperative"><div class="imperative-title">{title.strip()}</div>'
        
        # Format context sections
        content = re.sub(
            r'\*\*📋 Context:\*\*(.*?)(?=\*\*🚀|$)', 
            r'<div class="section-label"><span class="emoji">📋</span> Context:</div><div class="section-content">\1</div>', 
            content, 
            flags=re.DOTALL
        )
        
        # Format AI Agent Opportunity sections
        content = re.sub(
            r'\*\*🚀 AI Agent Opportunity:\*\*(.*?)(?=\*\*💰|$)', 
            r'<div class="section-label"><span class="emoji">🚀</span> AI Agent Opportunity:</div><div class="section-content">\1</div>', 
            content, 
            flags=re.DOTALL
        )
        
        # Format Expected Impact sections
        content = re.sub(
            r'\*\*💰 Expected Impact:\*\*(.*?)(?=###|##|$)', 
            r'<div class="section-label"><span class="emoji">💰</span> Expected Impact:</div><div class="section-content">\1</div>', 
            content, 
            flags=re.DOTALL
        )
        
        # Add the formatted content and close the imperative div
        result += content + '</div>'
        return result

    def _format_regular_content(self, content: str) -> str:
        """Format content that doesn't have strategic imperatives."""
        # Format context sections
        content = re.sub(
            r'\*\*📋 Context:\*\*(.*?)(?=\*\*🚀|$)', 
            r'<div class="section-label"><span class="emoji">📋</span> Context:</div><div class="section-content">\1</div>', 
            content, 
            flags=re.DOTALL
        )
        
        # Format AI Agent Opportunity sections
        content = re.sub(
            r'\*\*🚀 AI Agent Opportunity:\*\*(.*?)(?=\*\*💰|$)', 
            r'<div class="section-label"><span class="emoji">🚀</span> AI Agent Opportunity:</div><div class="section-content">\1</div>', 
            content, 
            flags=re.DOTALL
        )
        
        # Format Expected Impact sections
        content = re.sub(
            r'\*\*💰 Expected Impact:\*\*(.*?)(?=###|##|$)', 
            r'<div class="section-label"><span class="emoji">💰</span> Expected Impact:</div><div class="section-content">\1</div>', 
            content, 
            flags=re.DOTALL
        )
        
        return content

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