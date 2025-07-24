#!/usr/bin/env python3
"""
API Routes for Public Report Access

Handles API endpoints for viewing and downloading company reports:
- HTML report viewing
- PDF report downloads  
- Embeddable report versions
"""

import base64
import logging
from flask import Blueprint, request, Response, render_template, abort, make_response
from app.models.company import Company

logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/public/reports/<int:company_id>')
def get_company_report(company_id: int):
    """Serve HTML report for a company."""
    try:
        # Get company by ID
        company = Company.get_by_id(company_id)
        if not company:
            abort(404, description="Company not found")
        
        # Check if HTML report exists
        if not company.html_report:
            abort(404, description="Report not available for this company")
        
        # Return HTML report directly with proper content type
        response = make_response(company.html_report)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
        
    except Exception as e:
        logger.error(f"Error serving HTML report for company {company_id}: {e}")
        abort(500, description="Internal server error")

@api_bp.route('/public/reports/<int:company_id>/pdf')
def get_company_report_pdf(company_id: int):
    """Download PDF report for a company."""
    try:
        # Get company by ID
        company = Company.get_by_id(company_id)
        if not company:
            abort(404, description="Company not found")
        
        # Check if PDF report exists
        if not company.pdf_report_base64:
            abort(404, description="PDF report not available for this company - PDF generation may be disabled due to missing system dependencies")
        
        # Decode base64 PDF data
        try:
            pdf_bytes = base64.b64decode(company.pdf_report_base64)
        except Exception as e:
            logger.error(f"Error decoding PDF for company {company_id}: {e}")
            abort(500, description="Error processing PDF report")
        
        # Create safe filename
        safe_company_name = "".join(c for c in company.company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_company_name = safe_company_name.replace(' ', '_')
        filename = f"{safe_company_name}_Strategic_Report.pdf"
        
        # Return PDF with proper headers for download
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = len(pdf_bytes)
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving PDF report for company {company_id}: {e}")
        abort(500, description="Internal server error")

@api_bp.route('/public/reports/<int:company_id>/embed')
def get_company_report_embed(company_id: int):
    """Serve embeddable version of company report."""
    try:
        # Get company by ID
        company = Company.get_by_id(company_id)
        if not company:
            abort(404, description="Company not found")
        
        # Check if HTML report exists
        if not company.html_report:
            abort(404, description="Report not available for this company")
        
        # Process HTML for embedding (remove HTML/head/body tags, keep content)
        html_content = company.html_report
        
        # Extract content between body tags if they exist
        import re
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            content = body_match.group(1)
        else:
            content = html_content
        
        # Create embeddable version with minimal styling
        embeddable_html = f'''
        <div class="embedded-report" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 100%; padding: 20px; background: white;">
            <style>
                .embedded-report h1, .embedded-report h2, .embedded-report h3 {{
                    color: #2c3e50;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                .embedded-report .strategic-imperative {{
                    background: #f8f9fa;
                    border-left: 4px solid #007bff;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 0 4px 4px 0;
                }}
                .embedded-report .imperative-title {{
                    font-weight: bold;
                    font-size: 1.1em;
                    color: #007bff;
                    margin-bottom: 10px;
                }}
                .embedded-report .section-label {{
                    font-weight: bold;
                    color: #495057;
                    margin-top: 15px;
                    margin-bottom: 8px;
                }}
                .embedded-report .section-content {{
                    margin-bottom: 15px;
                    text-align: justify;
                }}
                .embedded-report .recommendations-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin: 20px 0;
                }}
                .embedded-report .priority-card {{
                    background: #fff;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .embedded-report .priority-title {{
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 15px;
                    font-size: 1.1em;
                }}
                .embedded-report .impact-list {{
                    list-style-type: disc;
                    margin-left: 20px;
                    margin-bottom: 15px;
                }}
                .embedded-report .impact-list li {{
                    margin-bottom: 8px;
                }}
                @media (max-width: 768px) {{
                    .embedded-report .recommendations-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
            {content}
        </div>
        '''
        
        # Return embeddable HTML
        response = make_response(embeddable_html)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['X-Frame-Options'] = 'ALLOWALL'  # Allow embedding in iframes
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving embeddable report for company {company_id}: {e}")
        abort(500, description="Internal server error")

@api_bp.route('/public/reports/<int:company_id>/info')
def get_company_report_info(company_id: int):
    """Get basic info about a company's report availability."""
    try:
        # Get company by ID
        company = Company.get_by_id(company_id)
        if not company:
            abort(404, description="Company not found")
        
        # Return report availability info
        info = {
            'company_id': company.id,
            'company_name': company.company_name,
            'website_url': company.website_url,
            'has_html_report': bool(company.html_report),
            'has_pdf_report': bool(company.pdf_report_base64),
            'research_status': company.research_status,
            'research_completed_at': company.research_completed_at.isoformat() if company.research_completed_at else None,
            'updated_at': company.updated_at.isoformat() if company.updated_at else None
        }
        
        response = make_response(info)
        response.headers['Content-Type'] = 'application/json'
        return response
        
    except Exception as e:
        logger.error(f"Error getting report info for company {company_id}: {e}")
        abort(500, description="Internal server error")

@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors for API routes."""
    return {
        'error': 'Not Found',
        'message': error.description or 'The requested resource was not found'
    }, 404

@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for API routes."""
    return {
        'error': 'Internal Server Error', 
        'message': error.description or 'An internal server error occurred'
    }, 500