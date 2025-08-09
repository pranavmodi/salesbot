#!/usr/bin/env python3
"""
LLM Report Generator

Handles the conversion of LLM step 3 markdown reports into formatted HTML reports
and manages the final report generation process.
"""

import os
import logging
import markdown
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class LLMReportGenerator:
    """Handles LLM report generation and formatting."""
    
    def __init__(self):
        load_dotenv()
        logger.info("LLMReportGenerator initialized")

    def generate_html_report(self, company_name: str, markdown_content: str, provider: str = 'claude') -> str:
        """
        Convert markdown report to formatted HTML.
        
        Args:
            company_name: Name of the company
            markdown_content: Markdown content from step 3
            provider: LLM provider used
            
        Returns:
            Formatted HTML report
        """
        logger.info(f"Generating HTML report for {company_name}")
        
        try:
            # Convert markdown to HTML
            md = markdown.Markdown(extensions=['tables', 'toc', 'codehilite'])
            html_content = md.convert(markdown_content)
            
            # Get current timestamp
            generated_at = datetime.now().strftime("%B %d, %Y")
            
            # Create complete HTML document with styling
            html_report = self._create_styled_html_report(
                company_name, 
                html_content, 
                generated_at, 
                provider
            )
            
            logger.info(f"Successfully generated HTML report for {company_name} ({len(html_report)} characters)")
            return html_report
            
        except Exception as e:
            logger.error(f"Error generating HTML report for {company_name}: {e}")
            return f"<html><body><h1>Error generating report for {company_name}</h1><p>{str(e)}</p></body></html>"

    def _create_styled_html_report(self, company_name: str, html_content: str, 
                                 generated_at: str, provider: str) -> str:
        """Create a fully styled HTML report matching the original strategic report format."""
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strategic Analysis: {company_name}</title>
    <style>
        /* Professional McKinsey-style CSS */
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fff;
        }}
        
        .header {{
            border-bottom: 3px solid #0066cc;
            padding-bottom: 20px;
            margin-bottom: 40px;
        }}
        
        h1 {{
            color: #0066cc;
            font-size: 2.2em;
            font-weight: 300;
            margin: 0 0 10px 0;
            letter-spacing: -0.5px;
        }}
        
        .company-name {{
            font-weight: 600;
            color: #333;
        }}
        
        h2 {{
            color: #0066cc;
            font-size: 1.4em;
            font-weight: 500;
            margin: 35px 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        h3 {{
            color: #333;
            font-size: 1.2em;
            font-weight: 600;
            margin: 25px 0 12px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .emoji {{
            font-size: 1.1em;
        }}
        
        .executive-summary {{
            background: #f8f9fa;
            padding: 25px;
            border-left: 4px solid #0066cc;
            margin: 25px 0;
            font-size: 1.05em;
        }}
        
        .executive-summary a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: bold;
        }}
        
        .executive-summary a:hover {{
            text-decoration: underline;
        }}
        
        .strategic-imperative {{
            background: #fff;
            border: 1px solid #e0e0e0;
            padding: 25px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .imperative-title {{
            font-size: 1.3em;
            font-weight: 600;
            color: #0066cc;
            margin-bottom: 15px;
        }}
        
        .section-label {{
            font-weight: 600;
            color: #555;
            margin: 15px 0 8px 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .section-content {{
            margin-bottom: 15px;
            padding-left: 20px;
        }}
        
        .recommendations-section {{
            margin: 30px 0;
        }}
        
        .recommendations-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        
        .priority-card {{
            background: #fff;
            border: 1px solid #e0e0e0;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .priority-title {{
            font-weight: 600;
            color: #0066cc;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .impact-list {{
            list-style: none;
            padding: 0;
        }}
        
        .impact-list li {{
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
            position: relative;
            padding-left: 20px;
        }}
        
        .impact-list li:before {{
            content: "▸";
            color: #0066cc;
            position: absolute;
            left: 0;
            font-weight: bold;
        }}
        
        .impact-section {{
            margin: 30px 0;
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
        }}
        
        .footer {{
            margin-top: 50px;
            padding-top: 25px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        
        .footer a {{
            color: #0066cc;
            text-decoration: none;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
        
        .generation-date {{
            font-style: italic;
            color: #888;
            margin-top: 5px;
        }}
        
        /* Print styles for PDF */
        @media print {{
            body {{
                padding: 20px;
            }}
            
            .recommendations-grid {{
                grid-template-columns: 1fr;
            }}
            
            .strategic-imperative {{
                page-break-inside: avoid;
            }}
        }}
        
        /* Mobile responsive */
        @media (max-width: 600px) {{
            .recommendations-grid {{
                grid-template-columns: 1fr;
            }}
            
            body {{
                padding: 20px 15px;
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Strategic Analysis: <span class="company-name">{company_name}</span></h1>
    </div>
    
    <div class="content-section">
        {html_content}
    </div>
    
    <div class="footer">
        <p><strong>Strategic analysis prepared by <a href="https://possibleminds.in" target="_blank">Possible Minds</a></strong></p>
        <div class="generation-date">Generated on {generated_at} using {provider} deep research</div>
    </div>
</body>
</html>"""
        
        return html_template

    def finalize_step_3_report(self, company_id: int, step_3_content: str, provider: str = 'claude') -> Dict[str, Any]:
        """
        Finalize step 3 by generating HTML and markdown reports and storing them.
        
        Args:
            company_id: Company ID
            step_3_content: Final report content from step 3
            provider: LLM provider used
            
        Returns:
            Dictionary with success status and report information
        """
        logger.info(f"Finalizing step 3 report for company {company_id}")
        
        try:
            from app.models.company import Company
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            # Use the canonical ReportGenerator + Jinja renderer so HTML matches the public endpoint format
            from deepresearch.report_generator import ReportGenerator
            
            # Get company
            company = Company.get_by_id(company_id)
            if not company:
                return {
                    'success': False,
                    'error': f'Company with ID {company_id} not found'
                }
            
            # Prefer generating via structured template using Step 1/2 outputs to ensure exact format
            basic_research = getattr(company, 'llm_research_step_1_basic', '') or getattr(company, 'research_step_1_basic', '')
            strategic_analysis = getattr(company, 'llm_research_step_2_strategic', '') or getattr(company, 'research_step_2_strategic', '')

            html_report: str
            try:
                if strategic_analysis:
                    generator = ReportGenerator()
                    report_bundle = generator.generate_strategic_report(
                        company.company_name,
                        basic_research,
                        strategic_analysis
                    )
                    html_report = report_bundle.get('html_report', '')
                else:
                    # Fallback: render markdown-based HTML if step 2 data missing
                    html_report = self.generate_html_report(company.company_name, step_3_content, provider)
            except Exception as render_err:
                logger.error(f"Primary renderer failed for company {company.id}, falling back to markdown HTML: {render_err}")
                html_report = self.generate_html_report(company.company_name, step_3_content, provider)
            
            # Store reports in database
            db_service = DatabaseService()
            
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_html_report = :html_report,
                            llm_markdown_report = :markdown_report,
                            llm_research_updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'html_report': html_report,
                        'markdown_report': step_3_content,
                        'company_id': company_id
                    })
            
            logger.info(f"Successfully finalized step 3 report for {company.company_name}")
            
            return {
                'success': True,
                'company_id': company_id,
                'company_name': company.company_name,
                'html_report_length': len(html_report),
                'markdown_report_length': len(step_3_content),
                'provider': provider
            }
            
        except Exception as e:
            logger.error(f"Error finalizing step 3 report for company {company_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }