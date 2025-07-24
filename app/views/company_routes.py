from flask import Blueprint, request, jsonify, current_app
import os
import subprocess
import threading

from app.models.company import Company

company_bp = Blueprint('company_api', __name__, url_prefix='/api')

@company_bp.route('/companies/extract', methods=['POST'])
def extract_companies():
    """Extract unique companies from contacts table and insert into companies table."""
    try:
        # Run the extraction script
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts', 'extract_companies.py')
        current_app.logger.info(f"Running company extraction script: {script_path}")
        
        result = subprocess.run([
            'python', script_path
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        if result.returncode == 0:
            current_app.logger.info(f"Company extraction completed successfully: {result.stdout}")
            return jsonify({
                'success': True,
                'message': 'Companies extracted successfully',
                'output': result.stdout.strip()
            })
        else:
            current_app.logger.error(f"Company extraction failed: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Company extraction failed',
                'error': result.stderr.strip()
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in company extraction: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Company extraction failed: {str(e)}'
        }), 500

@company_bp.route('/companies/research', methods=['POST'])
def research_companies():
    """Trigger company research for companies without research data."""
    try:
        data = request.get_json()
        max_companies = data.get('max_companies', 10) if data else 10
        force_refresh = data.get('force_refresh', False) if data else False
        
        # Import the new modular research system
        from deepresearch.company_researcher import CompanyResearcher
        
        current_app.logger.info(f"Starting company research with max_companies={max_companies}, force_refresh={force_refresh}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    researcher = CompanyResearcher()
                    
                    if force_refresh:
                        companies = researcher.database_service.get_all_companies()
                        app_instance.logger.info(f"Force refresh mode: processing all {len(companies)} companies")
                        companies_to_research = companies[:max_companies]
                    else:
                        companies_to_research = researcher.database_service.get_companies_without_research()
                        app_instance.logger.info(f"Found {len(companies_to_research)} companies without research")
                        companies_to_research = companies_to_research[:max_companies]
                    
                    app_instance.logger.info(f"Processing {len(companies_to_research)} companies")
                    
                    for company in companies_to_research:
                        try:
                            app_instance.logger.info(f"Researching company: {company.company_name}")
                            researcher.research_company(company, force_refresh=force_refresh)
                        except Exception as e:
                            app_instance.logger.error(f"Error researching company {company.company_name}: {str(e)}")
                    
                    app_instance.logger.info("Company research completed successfully")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error in background research process: {str(e)}")
        
        # Start the research in a background thread
        research_thread = threading.Thread(target=run_research)
        research_thread.daemon = False  # Allow proper cleanup
        research_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Company research started for up to {max_companies} companies. This process will run in the background.',
            'status': 'started',
            'force_refresh': force_refresh
        })
        
    except Exception as e:
        current_app.logger.error(f"Error starting company research: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to start company research: {str(e)}'
        }), 500

@company_bp.route('/companies', methods=['GET'])
def get_companies():
    """Get all companies with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = Company.get_paginated(page=page, per_page=per_page)
        
        # Convert companies to dict format
        companies_data = []
        for company in result['companies']:
            company_dict = company.to_dict()
            # Add a flag to indicate if research is needed
            company_dict['needs_research'] = not company.company_research or 'Research pending' in company.company_research
            companies_data.append(company_dict)
        
        return jsonify({
            'success': True,
            'companies': companies_data,
            'pagination': {
                'current_page': result['current_page'],
                'total_pages': result['total_pages'],
                'per_page': result['per_page'],
                'total_companies': result['total_companies']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting companies: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load companies'
        }), 500

@company_bp.route('/companies/<int:company_id>', methods=['GET'])
def get_company_details(company_id):
    """Get detailed information about a specific company."""
    try:
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        company_dict = company.to_dict()
        company_dict['needs_research'] = not company.company_research or 'Research pending' in company.company_research
        
        return jsonify({
            'success': True,
            'company': company_dict
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting company details: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load company details'
        }), 500

@company_bp.route('/companies/search', methods=['GET'])
def search_companies():
    """Search companies by name, website, or research content."""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        companies = Company.search(query)
        companies_data = []
        for company in companies:
            company_dict = company.to_dict()
            company_dict['needs_research'] = not company.company_research or 'Research pending' in company.company_research
            companies_data.append(company_dict)
        
        return jsonify({
            'success': True,
            'companies': companies_data,
            'count': len(companies_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error searching companies: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to search companies'
        }), 500

@company_bp.route('/companies/<int:company_id>/research', methods=['POST'])
def research_single_company(company_id):
    """Research a specific company by ID using step-by-step deep research."""
    try:
        data = request.get_json() or {}
        force_refresh = data.get('force_refresh', False)
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Import the new step-by-step research system
        from deepresearch.step_by_step_researcher import StepByStepResearcher
        
        current_app.logger.info(f"Starting step-by-step research for company ID {company_id}: {company.company_name}, force_refresh={force_refresh}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_step_by_step_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    researcher = StepByStepResearcher()
                    result = researcher.start_deep_research(company_id, force_refresh=force_refresh)
                    
                    if result['success']:
                        app_instance.logger.info(f"Step-by-step research completed successfully for {company.company_name}")
                    else:
                        app_instance.logger.error(f"Step-by-step research failed for {company.company_name}: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error in step-by-step research for company {company_id}: {str(e)}")
        
        # Start the research in a background thread
        research_thread = threading.Thread(target=run_step_by_step_research)
        research_thread.daemon = False  # Allow proper cleanup
        research_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Step-by-step deep research started for {company.company_name}. This process will run in the background.',
            'company_name': company.company_name,
            'status': 'started',
            'force_refresh': force_refresh,
            'research_type': 'step_by_step'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error starting step-by-step research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to start research: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/research/progress', methods=['GET'])
def get_research_progress(company_id):
    """Get research progress for a specific company."""
    try:
        from deepresearch.step_by_step_researcher import StepByStepResearcher
        
        researcher = StepByStepResearcher()
        progress = researcher.get_research_progress(company_id)
        
        return jsonify(progress)
        
    except Exception as e:
        current_app.logger.error(f"Error getting research progress for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get research progress: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/research/resume', methods=['POST'])
def resume_research(company_id):
    """Resume incomplete research for a specific company."""
    try:
        from deepresearch.step_by_step_researcher import StepByStepResearcher
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        current_app.logger.info(f"Resuming research for company ID {company_id}: {company.company_name}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_resume_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    researcher = StepByStepResearcher()
                    result = researcher.resume_research(company_id)
                    
                    if result['success']:
                        app_instance.logger.info(f"Resume research completed for {company.company_name}")
                    else:
                        app_instance.logger.error(f"Resume research failed for {company.company_name}: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error resuming research for company {company_id}: {str(e)}")
        
        # Start the resume in a background thread
        resume_thread = threading.Thread(target=run_resume_research)
        resume_thread.daemon = False  # Allow proper cleanup
        resume_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Resume research started for {company.company_name}. This process will run in the background.',
            'company_name': company.company_name,
            'status': 'resuming'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error resuming research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to resume research: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/research/step/<int:step>', methods=['GET'])
def get_research_step(company_id, step):
    """Get a specific research step content for a company."""
    try:
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        if step not in [1, 2, 3]:
            return jsonify({
                'success': False,
                'message': 'Invalid step number. Must be 1, 2, or 3.'
            }), 400
        
        step_titles = {
            1: 'Basic Company Research',
            2: 'Strategic Analysis',
            3: 'Final Report'
        }
        
        step_content = ''
        if step == 1:
            step_content = company.research_step_1_basic or ''
        elif step == 2:
            step_content = company.research_step_2_strategic or ''
        elif step == 3:
            step_content = company.research_step_3_report or ''
        
        return jsonify({
            'success': True,
            'company_name': company.company_name,
            'step': step,
            'step_title': step_titles[step],
            'content': step_content,
            'has_content': bool(step_content),
            'content_length': len(step_content)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting research step {step} for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get research step: {str(e)}'
        }), 500

@company_bp.route('/companies/clean-all-research', methods=['POST'])
def clean_all_research():
    """Clean all research data from all companies."""
    try:
        current_app.logger.info("Starting to clean all research data from companies")
        
        # Import and use the cleaner directly instead of running the script
        import sys
        import os
        
        # Add the scripts directory to the path
        scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts')
        if scripts_path not in sys.path:
            sys.path.append(scripts_path)
        
        from clear_company_research import CompanyResearchCleaner
        
        cleaner = CompanyResearchCleaner()
        
        # Get count before clearing
        count_before = cleaner.get_companies_with_research_count()
        current_app.logger.info(f"Found {count_before} companies with research data")
        
        if count_before == 0:
            return jsonify({
                'success': True,
                'message': 'No research data found to clean',
                'companies_affected': 0
            })
        
        # Perform the clearing
        success = cleaner.clear_all_research()
        
        if success:
            current_app.logger.info(f"Successfully cleaned research data from {count_before} companies")
            return jsonify({
                'success': True,
                'message': f'Successfully cleaned research data from {count_before} companies',
                'companies_affected': count_before
            })
        else:
            current_app.logger.error("Failed to clean research data")
            return jsonify({
                'success': False,
                'message': 'Failed to clean research data - database operation failed'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error cleaning all research data: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to clean research data: {str(e)}'
        }), 500
