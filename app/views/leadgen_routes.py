"""
Leadgen routes for Flask application.
Converts FastAPI endpoints to Flask routes.
"""
from flask import Blueprint, request, jsonify, render_template, send_file
from app.tenant import current_tenant_id
from leadgen.database import get_db_session
from app.models.leadgen_models import LeadgenCompany as Company, LeadgenJobPosting as JobPosting, LeadgenScrapingLog as ScrapingLog, LeadgenSeedingSession as SeedingSession
from leadgen.ats_scraper import ATSScraper
from leadgen.lead_scoring import LeadScoringEngine, score_company_by_id, save_lead_score_to_db
from leadgen.openai_enricher import OpenAICompanyEnricher
import json
import uuid
import logging
from datetime import datetime

leadgen_bp = Blueprint('leadgen', __name__, url_prefix='/leadgen')
logger = logging.getLogger(__name__)

# Background tasks storage (in production, use Redis or similar)
scraping_tasks = {}

@leadgen_bp.route('/')
def index():
    """Main leadgen interface"""
    return render_template('leadgen/index.html')

@leadgen_bp.route('/api/companies', methods=['GET'])
def get_companies():
    """Get all companies with optional filtering"""
    try:
        tenant_id = current_tenant_id()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        with get_db_session() as session:
            query = session.query(Company).filter(
                Company.salesbot_tenant_id == tenant_id
            )
            
            # Add filters if provided
            if request.args.get('qualified_only') == 'true':
                query = query.filter(Company.is_qualified_lead == True)
            
            if request.args.get('has_jobs') == 'true':
                query = query.filter(Company.support_roles_count > 0)
            
            # Pagination
            offset = (page - 1) * per_page
            companies = query.offset(offset).limit(per_page).all()
            total = query.count()
            
            return jsonify({
                'companies': [company.to_dict() for company in companies],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            })
            
    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
        return jsonify({'error': str(e)}), 500

@leadgen_bp.route('/api/companies/<int:company_id>', methods=['GET'])
def get_company(company_id):
    """Get a specific company with its job postings"""
    try:
        tenant_id = current_tenant_id()
        
        with get_db_session() as session:
            company = session.query(Company).filter(
                Company.id == company_id,
                Company.salesbot_tenant_id == tenant_id
            ).first()
            
            if not company:
                return jsonify({'error': 'Company not found'}), 404
            
            # Include job postings
            company_dict = company.to_dict()
            company_dict['job_postings'] = [job.to_dict() for job in company.job_postings]
            company_dict['scraping_logs'] = [log.to_dict() for log in company.scraping_logs]
            
            return jsonify(company_dict)
            
    except Exception as e:
        logger.error(f"Error fetching company {company_id}: {e}")
        return jsonify({'error': str(e)}), 500

@leadgen_bp.route('/api/start-scraping', methods=['POST'])
def start_scraping():
    """Start ATS scraping task"""
    try:
        tenant_id = current_tenant_id()
        data = request.json
        
        # Validate input
        companies = data.get('companies', [])
        if not companies:
            return jsonify({'error': 'No companies provided'}), 400
        
        task_id = str(uuid.uuid4())
        
        # Store task metadata
        scraping_tasks[task_id] = {
            'status': 'started',
            'progress': 0,
            'total': len(companies),
            'tenant_id': tenant_id,
            'started_at': datetime.utcnow(),
            'companies_processed': 0,
            'results': []
        }
        
        # TODO: In production, use background task queue (Celery, etc.)
        # For now, we'll process synchronously for small batches
        try:
            scraper = ATSScraper()
            results = []
            
            for i, company_name in enumerate(companies):
                try:
                    with get_db_session() as session:
                        # Find or create company
                        company = session.query(Company).filter(
                            Company.name == company_name,
                            Company.salesbot_tenant_id == tenant_id
                        ).first()
                        
                        if not company:
                            company = Company(
                                name=company_name,
                                source='ats_scraping',
                                salesbot_tenant_id=tenant_id
                            )
                            session.add(company)
                            session.flush()
                        
                        # Update task progress
                        scraping_tasks[task_id]['progress'] = i + 1
                        scraping_tasks[task_id]['companies_processed'] = i + 1
                        
                        results.append({
                            'company_id': company.id,
                            'company_name': company_name,
                            'status': 'processed'
                        })
                        
                except Exception as company_error:
                    logger.error(f"Error processing company {company_name}: {company_error}")
                    results.append({
                        'company_name': company_name,
                        'status': 'error',
                        'error': str(company_error)
                    })
            
            scraping_tasks[task_id]['status'] = 'completed'
            scraping_tasks[task_id]['results'] = results
            
        except Exception as scraping_error:
            scraping_tasks[task_id]['status'] = 'failed'
            scraping_tasks[task_id]['error'] = str(scraping_error)
        
        return jsonify({
            'task_id': task_id,
            'status': 'started',
            'message': f'Started scraping {len(companies)} companies'
        })
        
    except Exception as e:
        logger.error(f"Error starting scraping: {e}")
        return jsonify({'error': str(e)}), 500

@leadgen_bp.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get scraping task status"""
    if task_id not in scraping_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = scraping_tasks[task_id]
    
    # Check tenant access
    if task.get('tenant_id') != current_tenant_id():
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'task_id': task_id,
        'status': task['status'],
        'progress': task['progress'],
        'total': task['total'],
        'companies_processed': task['companies_processed'],
        'results': task.get('results', []),
        'error': task.get('error')
    })

@leadgen_bp.route('/api/companies/<int:company_id>/enrich', methods=['POST'])
def enrich_company(company_id):
    """Enrich a company using OpenAI"""
    try:
        tenant_id = current_tenant_id()
        
        with get_db_session() as session:
            company = session.query(Company).filter(
                Company.id == company_id,
                Company.salesbot_tenant_id == tenant_id
            ).first()
            
            if not company:
                return jsonify({'error': 'Company not found'}), 404
            
            # Initialize enricher
            enricher = OpenAICompanyEnricher()
            
            # Enrich company
            enriched_data = enricher.enrich_company(company.name)
            
            if enriched_data:
                # Update company with enriched data
                if enriched_data.get('domain'):
                    company.domain = enriched_data['domain']
                if enriched_data.get('industry'):
                    company.industry = enriched_data['industry']
                if enriched_data.get('employee_count'):
                    company.employee_count = enriched_data['employee_count']
                if enriched_data.get('location'):
                    company.location = enriched_data['location']
                if enriched_data.get('linkedin_url'):
                    company.linkedin_url = enriched_data['linkedin_url']
                
                company.updated_at = datetime.utcnow()
                session.commit()
                
                return jsonify({
                    'success': True,
                    'company': company.to_dict(),
                    'enriched_data': enriched_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No enrichment data available'
                }), 400
                
    except Exception as e:
        logger.error(f"Error enriching company {company_id}: {e}")
        return jsonify({'error': str(e)}), 500

@leadgen_bp.route('/api/companies/<int:company_id>/score', methods=['POST'])
def score_company(company_id):
    """Score a company using the lead scoring engine"""
    try:
        tenant_id = current_tenant_id()
        
        with get_db_session() as session:
            company = session.query(Company).filter(
                Company.id == company_id,
                Company.salesbot_tenant_id == tenant_id
            ).first()
            
            if not company:
                return jsonify({'error': 'Company not found'}), 404
            
            # Score the company
            score_result = score_company_by_id(company_id, session)
            
            if score_result:
                return jsonify({
                    'success': True,
                    'company_id': company_id,
                    'score': score_result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to score company'
                }), 400
                
    except Exception as e:
        logger.error(f"Error scoring company {company_id}: {e}")
        return jsonify({'error': str(e)}), 500

@leadgen_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get leadgen statistics for the current tenant"""
    try:
        tenant_id = current_tenant_id()
        
        with get_db_session() as session:
            total_companies = session.query(Company).filter(
                Company.salesbot_tenant_id == tenant_id
            ).count()
            
            qualified_leads = session.query(Company).filter(
                Company.salesbot_tenant_id == tenant_id,
                Company.is_qualified_lead == True
            ).count()
            
            companies_with_jobs = session.query(Company).filter(
                Company.salesbot_tenant_id == tenant_id,
                Company.support_roles_count > 0
            ).count()
            
            total_jobs = session.query(JobPosting).join(Company).filter(
                Company.salesbot_tenant_id == tenant_id
            ).count()
            
            return jsonify({
                'total_companies': total_companies,
                'qualified_leads': qualified_leads,
                'companies_with_jobs': companies_with_jobs,
                'total_jobs': total_jobs
            })
            
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': str(e)}), 500