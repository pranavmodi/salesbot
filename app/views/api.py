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
from flask import Blueprint, request, Response, render_template, abort, make_response, jsonify
from app.models.company import Company
from app.models.contact import Contact

logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/contacts', methods=['POST'])
def add_contact():
    """Add a new contact via API."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # For now, return success - the actual implementation would save to database
        return jsonify({'success': True, 'message': 'Contact added successfully'})
    except Exception as e:
        logger.error(f"Error adding contact: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_bp.route('/companies', methods=['GET'])
@api_bp.route('/companies/list', methods=['GET'])
def get_companies():
    """Get companies list via API."""
    try:
        companies = Company.get_paginated()
        # Convert to JSON-serializable format
        companies_data = []
        for company in companies.get('companies', []):
            companies_data.append({
                'id': company.id,
                'company_name': company.company_name,
                'website_url': company.website_url,
                'created_at': company.created_at.isoformat() if company.created_at else None,
                # Research status fields for smart status badges
                'company_research': bool(getattr(company, 'company_research', None)),
                'llm_research_step_status': getattr(company, 'llm_research_step_status', None),
                'llm_research_provider': getattr(company, 'llm_research_provider', None),
                'llm_research_started_at': getattr(company, 'llm_research_started_at', None),
                'llm_research_step_1_basic': bool(getattr(company, 'llm_research_step_1_basic', None)),
                'llm_research_step_2_strategic': bool(getattr(company, 'llm_research_step_2_strategic', None)),
                'llm_research_step_3_report': bool(getattr(company, 'llm_research_step_3_report', None))
            })
        return jsonify({'success': True, 'companies': companies_data})
    except Exception as e:
        logger.error(f"Error getting companies: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_bp.route('/companies', methods=['POST'])
def create_company():
    """Create a new company."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Validate required fields
        company_name = data.get('company_name', '').strip()
        if not company_name:
            return jsonify({'success': False, 'message': 'Company name is required'}), 400
        
        # Check if company already exists
        existing_companies = Company.get_companies_by_name(company_name)
        if existing_companies:
            return jsonify({'success': False, 'message': 'A company with this name already exists'}), 400
        
        # Prepare company data
        website_url = data.get('website_url', '').strip()
        if website_url and not website_url.startswith(('http://', 'https://')):
            website_url = f"https://{website_url}"
        
        company_data = {
            'company_name': company_name,
            'website_url': website_url,
            'company_research': ''  # Start with empty research
        }
        
        # Save the company
        success = Company.save(company_data)
        if success:
            # Get the created company to return its ID
            created_companies = Company.get_companies_by_name(company_name)
            if created_companies:
                company = created_companies[0]
                logger.info(f"Successfully created company: {company_name}")
                return jsonify({
                    'success': True,
                    'message': f'Company "{company_name}" created successfully',
                    'company': {
                        'id': company.id,
                        'company_name': company.company_name,
                        'website_url': company.website_url
                    }
                })
        
        return jsonify({'success': False, 'message': 'Failed to create company'}), 500
        
    except Exception as e:
        logger.error(f"Error creating company: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_bp.route('/public/reports/<int:company_id>')
def get_company_report(company_id: int):
    """Serve HTML report for a company."""
    try:
        # Get company by ID
        company = Company.get_by_id(company_id)
        if not company:
            abort(404, description="Company not found")
        
        # Check if HTML report exists (traditional or LLM research)
        html_report = getattr(company, 'html_report', '') or getattr(company, 'llm_html_report', '')
        if not html_report:
            abort(404, description="Report not available for this company")
        
        # Return HTML report directly with proper content type
        response = make_response(html_report)
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
        
        # Check if PDF report exists (traditional or LLM research)
        pdf_data = getattr(company, 'pdf_report_base64', '') or getattr(company, 'llm_pdf_report_base64', '')
        if not pdf_data:
            abort(404, description="PDF report not available for this company - PDF generation may be disabled due to missing system dependencies")
        
        # Decode base64 PDF data
        try:
            pdf_bytes = base64.b64decode(pdf_data)
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
        # Render inline in browser
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        response.headers['Content-Length'] = len(pdf_bytes)
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving PDF report for company {company_id}: {e}")
        abort(500, description="Internal server error")

@api_bp.route('/public/reports/<int:company_id>/basic-research.pdf')
def get_basic_research_pdf(company_id: int):
    """Download Basic Research (Step 1) PDF for a company."""
    try:
        company = Company.get_by_id(company_id)
        if not company:
            abort(404, description="Company not found")

        pdf_data = getattr(company, 'basic_research_pdf_base64', '')
        if not pdf_data:
            abort(404, description="Basic research PDF not available for this company")

        import base64
        try:
            pdf_bytes = base64.b64decode(pdf_data)
        except Exception as e:
            logger.error(f"Error decoding basic research PDF for company {company_id}: {e}")
            abort(500, description="Error processing basic research PDF")

        safe_company_name = "".join(c for c in company.company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_company_name = safe_company_name.replace(' ', '_')
        filename = f"{safe_company_name}_Basic_Research.pdf"

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        # Render inline in browser
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        response.headers['Content-Length'] = len(pdf_bytes)
        return response
    
    except Exception as e:
        logger.error(f"Error serving basic research PDF for company {company_id}: {e}")
        abort(500, description="Internal server error")

@api_bp.route('/public/reports/<int:company_id>/embed')
def get_company_report_embed(company_id: int):
    """Serve embeddable version of company report."""
    try:
        # Get company by ID
        company = Company.get_by_id(company_id)
        if not company:
            abort(404, description="Company not found")
        
        # Check if HTML report exists (traditional or LLM research)
        html_content = getattr(company, 'html_report', '') or getattr(company, 'llm_html_report', '')
        if not html_content:
            abort(404, description="Report not available for this company")
        
        # Process HTML for embedding (remove HTML/head/body tags, keep content)
        
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
            'has_html_report': bool(getattr(company, 'html_report', '') or getattr(company, 'llm_html_report', '')),
            'has_pdf_report': bool(getattr(company, 'pdf_report_base64', '') or getattr(company, 'llm_pdf_report_base64', '')),
            'has_basic_research_pdf': bool(getattr(company, 'basic_research_pdf_base64', '')),
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

@api_bp.route('/companies/<int:company_id>/generate-pdfs', methods=['POST'])
def generate_company_pdfs(company_id: int):
    """Generate and store PDFs for final report and basic research for a company."""
    try:
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({'success': False, 'error': 'Company not found'}), 404

        # Ensure Step 3 content exists
        step3_content = getattr(company, 'llm_research_step_3_report', '') or getattr(company, 'research_step_3_report', '')
        if not step3_content:
            return jsonify({'success': False, 'error': 'Step 3 report content not found; run report generation first.'}), 400

        # Use LLMReportGenerator finalization to generate/store HTML and PDFs
        from deepresearch.llm_report_generator import LLMReportGenerator
        provider = getattr(company, 'llm_research_provider', '') or 'claude'
        result = LLMReportGenerator().finalize_step_3_report(company_id, step3_content, provider)

        if not result or not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error', 'Failed to generate PDFs')}), 500

        # Re-fetch info flags for client convenience
        refreshed = Company.get_by_id(company_id)
        return jsonify({
            'success': True,
            'message': 'PDFs generated successfully',
            'has_pdf_report': bool(getattr(refreshed, 'pdf_report_base64', '') or getattr(refreshed, 'llm_pdf_report_base64', '')),
            'has_basic_research_pdf': bool(getattr(refreshed, 'basic_research_pdf_base64', '')),
            'details': {
                'llm_pdf_report_saved': result.get('llm_pdf_report_saved', False),
                'basic_research_pdf_saved': result.get('basic_research_pdf_saved', False)
            }
        })
    except Exception as e:
        logger.error(f"Error generating PDFs for company {company_id}: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors for API routes."""
    return {
        'error': 'Not Found',
        'message': error.description or 'The requested resource was not found'
    }, 404

@api_bp.route('/clean-database', methods=['POST'])
def clean_database():
    """Execute the database cleaning operation for current tenant only."""
    try:
        from app.services.database_cleaner import DatabaseCleanerService
        from flask import g
        
        # Get the current tenant ID
        tenant_id = getattr(g, 'tenant_id', None)
        if not tenant_id:
            return jsonify({
                'success': False, 
                'error': 'No tenant context available. Please login again.'
            }), 400
        
        logger.info(f"Starting database cleaning for tenant {tenant_id} via API")
        
        # Initialize the database cleaner service
        cleaner = DatabaseCleanerService()
        
        # Execute the tenant-specific cleaning operation
        result = cleaner.execute_complete_clean(tenant_id=tenant_id)
        
        if result['success']:
            logger.info(f"Database cleaning completed: {result['message']}")
            return jsonify({
                'success': True, 
                'message': result['message'],
                'details': result['details']
            })
        else:
            logger.error(f"Database cleaning failed: {result['message']}")
            return jsonify({
                'success': False, 
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"Error cleaning database: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Log Management API Routes
@api_bp.route('/logs/info', methods=['GET'])
def get_log_info():
    """Get information about application log files."""
    try:
        from app.utils.log_manager import log_manager
        info = log_manager.get_log_info()
        return jsonify({
            'success': True,
            'log_info': info
        })
    except Exception as e:
        logger.error(f"Error getting log info: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting log info: {str(e)}'
        }), 500

@api_bp.route('/logs/tail', methods=['GET'])
def get_log_tail():
    """Get the last N lines from the current log file."""
    try:
        from app.utils.log_manager import log_manager
        lines = request.args.get('lines', 100, type=int)
        lines = min(lines, 1000)  # Limit to prevent huge responses
        
        log_lines = log_manager.read_log_tail(lines=lines)
        return jsonify({
            'success': True,
            'lines': log_lines,
            'count': len(log_lines)
        })
    except Exception as e:
        logger.error(f"Error getting log tail: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting log tail: {str(e)}'
        }), 500

@api_bp.route('/logs/search', methods=['GET'])
def search_logs():
    """Search for specific terms in log files."""
    try:
        from app.utils.log_manager import log_manager
        search_term = request.args.get('q', '').strip()
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        
        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Search term is required'
            }), 400
        
        results = log_manager.search_logs(search_term, case_sensitive)
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'search_term': search_term
        })
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        return jsonify({
            'success': False,
            'message': f'Error searching logs: {str(e)}'
        }), 500

@api_bp.route('/logs/errors', methods=['GET'])
def get_recent_errors():
    """Get recent error and warning log entries."""
    try:
        from app.utils.log_manager import log_manager
        hours = request.args.get('hours', 24, type=int)
        hours = min(hours, 168)  # Limit to 1 week max
        
        errors = log_manager.get_recent_errors(hours=hours)
        return jsonify({
            'success': True,
            'errors': errors,
            'count': len(errors),
            'hours': hours
        })
    except Exception as e:
        logger.error(f"Error getting recent errors: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting recent errors: {str(e)}'
        }), 500

@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for API routes."""
    return {
        'error': 'Internal Server Error', 
        'message': error.description or 'An internal server error occurred'
    }, 500