from flask import Blueprint, request, jsonify, current_app, g
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

@company_bp.route('/companies/<int:company_id>/llm-deep-research', methods=['POST'])
def llm_deep_research_company(company_id):
    """Research a specific company using LLM deep research capabilities."""
    try:
        data = request.get_json() or {}
        force_refresh_raw = data.get('force_refresh', False)
        provider = data.get('provider', 'claude')  # Default to Claude, but support others
        
        # Handle force_refresh parameter - convert to boolean if it's an object
        if isinstance(force_refresh_raw, dict):
            force_refresh = bool(force_refresh_raw.get('isTrusted', False))
            current_app.logger.warning(f"Received JavaScript event object for force_refresh: {force_refresh_raw}, converted to: {force_refresh}")
        else:
            force_refresh = bool(force_refresh_raw)
        
        current_app.logger.info(f"Parameters: provider={provider}, force_refresh={force_refresh} (type: {type(force_refresh)})")
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Import the LLM Deep Research service
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        
        current_app.logger.critical(f"🚨 LLM DEEP RESEARCH API ENDPOINT CALLED: company_id={company_id}, company={company.company_name}, provider={provider}, force_refresh={force_refresh}, endpoint=/llm-deep-research")
        current_app.logger.info(f"Starting LLM deep research for company ID {company_id}: {company.company_name}, provider={provider}, force_refresh={force_refresh}")
        
        # BULLETPROOF: Check database status before allowing research  
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        temp_service = LLMDeepResearchService()
        
        if not force_refresh:
            try:
                status_check = temp_service._check_database_research_status(company_id)
                if status_check['already_triggered']:
                    current_app.logger.error(f"🚨 ENDPOINT BLOCKED: Deep research already triggered for company {company_id}, status: {status_check['status']}")
                    return jsonify({
                        'success': False,
                        'message': f'Deep research already triggered for {company.company_name}',
                        'current_status': status_check['status'],
                        'started_at': str(status_check.get('started_at', '')),
                        'error': 'Research already triggered. Please wait for completion or use force refresh.'
                    }), 409  # Conflict status code
            except Exception as check_error:
                current_app.logger.warning(f"Database status check failed, proceeding with caution: {check_error}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_llm_deep_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    llm_service = LLMDeepResearchService()
                    
                    # Execute the full research using the new 3-step workflow
                    app_instance.logger.info(f"Starting complete 3-step LLM research workflow for {company.company_name} using {provider}")
                    
                    # Execute step 1 (deep research) using the selected provider
                    step_1_results = llm_service.research_company_deep(
                        company.company_name, 
                        company.company_website or "",
                        provider=provider,
                        company_id=company_id
                    )
                    
                    if step_1_results and step_1_results != "__BACKGROUND_JOB_STARTED__":
                        # Step 1 completed immediately, continue with workflow
                        from deepresearch.llm_workflow_orchestrator import LLMWorkflowOrchestrator
                        orchestrator = LLMWorkflowOrchestrator(llm_service.openai_client)
                        
                        # Process step 1 completion and continue to step 2 & 3
                        orchestrator.process_step_1_completion_and_start_step_2(
                            company_id,
                            company.company_name,
                            company.company_website or "",
                            step_1_results
                        )
                        
                        app_instance.logger.info(f"Successfully completed full 3-step workflow for {company.company_name}")
                        
                    elif step_1_results == "__BACKGROUND_JOB_STARTED__":
                        # OpenAI background job started, workflow will continue via polling
                        app_instance.logger.info(f"OpenAI background job started for {company.company_name}, workflow will continue automatically")
                        
                    else:
                        # Step 1 failed
                        app_instance.logger.error(f"Step 1 research failed for {company.company_name}")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error in LLM 3-step research workflow for {company_id}: {str(e)}")
        
        # Start the complete research workflow in a background thread
        research_thread = threading.Thread(target=run_llm_deep_research)
        research_thread.daemon = False
        research_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Complete 3-step LLM research workflow initiated for {company.company_name} using {provider}. This includes step 1 (research), step 2 (strategic analysis), and step 3 (report generation).',
            'company_name': company.company_name,
            'status': 'workflow_initiated',
            'force_refresh': force_refresh,
            'research_type': '3_step_llm_workflow',
            'provider': provider,
            'next_step': f'The complete research workflow is running in the background using {provider}. Step 2 will automatically generate structured JSON strategic analysis.'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error starting LLM deep research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to start LLM deep research: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-research-results', methods=['POST'])
def submit_llm_research_results(company_id):
    """Submit LLM deep research results for processing and storage."""
    try:
        data = request.get_json()
        if not data or 'research_results' not in data:
            return jsonify({
                'success': False,
                'message': 'Research results are required'
            }), 400
        
        research_results = data['research_results']
        provider = data.get('provider', 'claude')
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Import required services
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        from deepresearch.database_service import DatabaseService
        
        current_app.logger.info(f"Processing LLM deep research results for company ID {company_id}: {company.company_name}, provider={provider}")
        
        # Process and validate the research results
        llm_service = LLMDeepResearchService()
        
        # Validate the research quality
        validation_results = llm_service.validate_research_quality(research_results)
        
        if not validation_results['is_valid']:
            current_app.logger.warning(f"Research quality validation failed for {company.company_name}: {validation_results['issues']}")
            return jsonify({
                'success': False,
                'message': 'Research quality validation failed',
                'validation_issues': validation_results['issues'],
                'quality_score': validation_results['quality_score']
            }), 400
        
        # Format the research for storage
        formatted_research = llm_service.format_research_for_system(research_results)
        formatted_research['research_method'] = f'{provider}_deep_research'
        
        # Store the research results in the new 3-step workflow format
        from deepresearch.llm_workflow_orchestrator import LLMWorkflowOrchestrator
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        
        # Store step 1 results in the correct field for the new workflow
        llm_service = LLMDeepResearchService()
        orchestrator = LLMWorkflowOrchestrator(llm_service.openai_client)
        
        current_app.logger.info(f"Processing manual paste as step 1 and continuing with step 2 & 3 for {company.company_name}")
        
        try:
            # Use the workflow orchestrator to process step 1 completion and start step 2
            # This will store step 1 results and automatically continue to step 2 and 3
            orchestrator.process_step_1_completion_and_start_step_2(
                company_id, 
                company.company_name, 
                company.company_website or "",
                research_results
            )
            
            current_app.logger.info(f"Successfully processed manual paste and triggered step 2 & 3 for {company.company_name}")
            return jsonify({
                'success': True,
                'message': f'Research results processed successfully for {company.company_name}. Step 2 (strategic analysis) and Step 3 (report generation) have been initiated.',
                'company_name': company.company_name,
                'research_method': f'{provider}_deep_research',
                'provider': provider,
                'word_count': formatted_research['word_count'],
                'character_count': formatted_research['character_count'],
                'quality_score': validation_results['quality_score'],
                'validation_status': 'passed',
                'next_steps': 'Step 2 (strategic analysis) and Step 3 (report generation) are now running in the background'
            })
            
        except Exception as workflow_error:
            current_app.logger.error(f"Error in workflow orchestrator for {company.company_name}: {workflow_error}")
            
            # Fallback: Store in old format if workflow fails
            db_service = DatabaseService()
            success = db_service.store_llm_research_results(
                company_id,
                research_results,
                formatted_research,
                validation_results
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Research results stored (legacy format) for {company.company_name}. Workflow continuation failed: {str(workflow_error)}',
                    'company_name': company.company_name,
                    'warning': 'Step 2 and 3 were not automatically triggered due to workflow error',
                    'research_method': formatted_research['research_method'],
                    'provider': provider,
                    'word_count': formatted_research['word_count'],
                    'character_count': formatted_research['character_count'],
                    'quality_score': validation_results['quality_score'],
                    'validation_status': 'passed'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Failed to store research results and workflow failed: {str(workflow_error)}'
                }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error processing LLM research results for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to process research results: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-research-status', methods=['GET'])
def get_llm_research_status(company_id):
    """Get the status of LLM deep research for a specific company."""
    try:
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Check for LLM research data
        has_llm_prompt = hasattr(company, 'llm_research_prompt') and company.llm_research_prompt
        has_llm_results = hasattr(company, 'llm_research_results') and company.llm_research_results
        llm_status = getattr(company, 'llm_research_status', 'not_started')
        research_method = getattr(company, 'llm_research_method', None)
        
        status_info = {
            'company_id': company_id,
            'company_name': company.company_name,
            'llm_research_status': llm_status,
            'has_prompt': has_llm_prompt,
            'has_results': has_llm_results,
            'is_ready_for_research': has_llm_prompt and not has_llm_results,
            'is_complete': has_llm_results,
            'research_method': research_method
        }
        
        # Add metadata if available
        if has_llm_results:
            status_info['last_updated'] = getattr(company, 'llm_research_updated_at', None)
            status_info['word_count'] = getattr(company, 'llm_research_word_count', 0)
            status_info['character_count'] = getattr(company, 'llm_research_character_count', 0)
            status_info['quality_score'] = getattr(company, 'llm_research_quality_score', 0)
        
        # Extract provider from research method if available
        if research_method:
            provider = research_method.replace('_deep_research', '') if '_deep_research' in research_method else research_method
            status_info['provider'] = provider
        
        return jsonify({
            'success': True,
            **status_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting LLM research status for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get research status: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-step-research', methods=['POST'])
def llm_step_research_company(company_id):
    """Start LLM step-by-step research for a specific company."""
    try:
        data = request.get_json() or {}
        provider = data.get('provider', 'claude')
        force_refresh_raw = data.get('force_refresh', False)
        
        # Handle force_refresh parameter - convert to boolean if it's an object
        if isinstance(force_refresh_raw, dict):
            force_refresh = bool(force_refresh_raw.get('isTrusted', False))
            current_app.logger.warning(f"Received JavaScript event object for force_refresh: {force_refresh_raw}, converted to: {force_refresh}")
        else:
            force_refresh = bool(force_refresh_raw)
        
        current_app.logger.info(f"Parameters: provider={provider}, force_refresh={force_refresh} (type: {type(force_refresh)})")
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Import the LLM Step-by-Step Researcher
        from deepresearch.llm_step_by_step_researcher import LLMStepByStepResearcher
        
        current_app.logger.critical(f"🚨 LLM STEP RESEARCH API ENDPOINT CALLED: company_id={company_id}, company={company.company_name}, provider={provider}, endpoint=/llm-step-research")
        current_app.logger.info(f"Starting LLM step research for company ID {company_id}: {company.company_name}, provider={provider}")
        
        # BULLETPROOF: Check database status before allowing research
        from deepresearch.llm_step_by_step_researcher import LLMStepByStepResearcher
        temp_researcher = LLMStepByStepResearcher()
        
        if not force_refresh:
            try:
                status_check = temp_researcher._check_step_research_status(company_id)
                if status_check['already_in_progress']:
                    current_app.logger.error(f"🚨 ENDPOINT BLOCKED: Research already in progress for company {company_id}, status: {status_check['status']}")
                    return jsonify({
                        'success': False,
                        'message': f'Research already in progress for {company.company_name}',
                        'current_status': status_check['status'],
                        'started_at': str(status_check.get('started_at', '')),
                        'error': 'Research already triggered. Please wait for completion or use force refresh.'
                    }), 409  # Conflict status code
            except Exception as check_error:
                current_app.logger.warning(f"Database status check failed, proceeding with caution: {check_error}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_llm_step_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    researcher = LLMStepByStepResearcher()
                    result = researcher.start_llm_step_research(company_id, provider, force_refresh)
                    
                    if result['success']:
                        app_instance.logger.info(f"LLM step research initiated for {company.company_name}: {result['current_step']}")
                    else:
                        app_instance.logger.error(f"LLM step research failed for {company.company_name}: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error in LLM step research for company {company_id}: {str(e)}")
        
        # Start the research in a background thread
        research_thread = threading.Thread(target=run_llm_step_research)
        research_thread.daemon = False
        research_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'LLM step-by-step research initiated for {company.company_name}. The process will run in the background.',
            'company_name': company.company_name,
            'provider': provider,
            'force_refresh': force_refresh,
            'research_type': 'llm_step_by_step',
            'status': 'started'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error starting LLM step research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to start LLM step research: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-step-results', methods=['POST'])
def submit_llm_step_results(company_id):
    """Submit results for a specific LLM research step."""
    try:
        data = request.get_json()
        if not data or 'step' not in data or 'results' not in data:
            return jsonify({
                'success': False,
                'message': 'Step and results are required'
            }), 400
        
        step = data['step']
        results = data['results']
        provider = data.get('provider', 'claude')
        
        if step not in ['step_1', 'step_2', 'step_3']:
            return jsonify({
                'success': False,
                'message': 'Invalid step. Must be step_1, step_2, or step_3'
            }), 400
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Import the LLM Step-by-Step Researcher
        from deepresearch.llm_step_by_step_researcher import LLMStepByStepResearcher
        
        current_app.logger.info(f"Submitting LLM step {step} results for company ID {company_id}: {company.company_name}")
        
        researcher = LLMStepByStepResearcher()
        result = researcher.submit_step_results(company_id, step, results, provider)
        
        if result['success']:
            current_app.logger.info(f"Successfully submitted step {step} results for {company.company_name}")
            return jsonify(result)
        else:
            current_app.logger.error(f"Failed to submit step {step} results for {company.company_name}: {result.get('error', 'Unknown error')}")
            return jsonify(result), 400
        
    except Exception as e:
        current_app.logger.error(f"Error submitting LLM step results for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to submit step results: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-step-progress', methods=['GET'])
def get_llm_step_progress(company_id):
    """Get progress for LLM step-by-step research."""
    try:
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Get progress directly without creating researcher instance for better performance
        # Check step completion status
        has_step_1 = hasattr(company, 'llm_research_step_1_basic') and company.llm_research_step_1_basic
        has_step_2 = hasattr(company, 'llm_research_step_2_strategic') and company.llm_research_step_2_strategic
        has_step_3 = (hasattr(company, 'llm_html_report') and company.llm_html_report) or (hasattr(company, 'html_report') and company.html_report)
        
        # Check for errors in steps
        step_1_has_error = has_step_1 and company.llm_research_step_1_basic.startswith('ERROR:')
        step_2_has_error = has_step_2 and company.llm_research_step_2_strategic.startswith('ERROR:')
        step_3_has_error = has_step_3 and ((hasattr(company, 'llm_html_report') and company.llm_html_report and company.llm_html_report.startswith('ERROR:')) or (hasattr(company, 'html_report') and company.html_report and company.html_report.startswith('ERROR:')))
        
        # Determine overall status
        current_status = getattr(company, 'llm_research_step_status', 'pending')
        
        if step_3_has_error or step_2_has_error or step_1_has_error:
            status = 'error'
        elif has_step_3 and not step_3_has_error:
            status = 'completed'
        elif current_status and ('executing' in current_status.lower() or 'progress' in current_status.lower() or 'queued' in current_status.lower() or 'background_job_running' in current_status.lower()):
            status = 'in_progress'
        else:
            status = 'pending'
        
        # Calculate numeric steps completed and progress percentage
        step_completions = [
            bool(has_step_1 and not step_1_has_error),
            bool(has_step_2 and not step_2_has_error), 
            bool(has_step_3 and not step_3_has_error)
        ]
        steps_completed_count = sum(step_completions)
        total_steps = 3
        progress_percentage = (steps_completed_count / total_steps) * 100
        
        # Determine current step and completion status BEFORE creating step details
        if steps_completed_count == total_steps:
            current_step = 'completed'
            is_complete = True
        elif step_1_has_error:
            current_step = 'step_1'
            is_complete = False
        elif step_2_has_error:
            current_step = 'step_2'
            is_complete = False
        elif step_3_has_error:
            current_step = 'step_3'
            is_complete = False
        elif not has_step_1:
            current_step = 'step_1'
            is_complete = False
        elif not has_step_2:
            current_step = 'step_2'
            is_complete = False
        elif not has_step_3:
            current_step = 'step_3'
            is_complete = False
        else:
            current_step = 'completed'
            is_complete = True
        
        # Check if step 1 was manually pasted
        is_manual_paste = current_status == 'step_1_completed_manual'
        
        # Create step details array for frontend
        step_details = [
            {
                'step': 1,
                'name': 'LLM Basic Research' + (' (Manual Paste)' if is_manual_paste else ''),
                'description': 'Comprehensive company intelligence gathering using LLM deep research' + (' - Content was manually pasted by user' if is_manual_paste else ''),
                'status': 'in_progress' if (current_status and ('queued' in current_status.lower() or 'progress' in current_status.lower() or 'executing' in current_status.lower()) and current_step == 'step_1') else ('error' if step_1_has_error else ('completed' if has_step_1 else 'pending')),
                'has_prompt': has_step_1,
                'has_results': has_step_1 and not step_1_has_error,
                'has_error': step_1_has_error and not (current_status and ('queued' in current_status.lower() or 'progress' in current_status.lower())),
                'error_message': company.llm_research_step_1_basic.replace('ERROR: ', '') if step_1_has_error and not (current_status and ('queued' in current_status.lower() or 'progress' in current_status.lower())) else None,
                'manual_paste': is_manual_paste
            },
            {
                'step': 2,
                'name': 'LLM Strategic Analysis',
                'description': 'Strategic imperatives and AI agent recommendations',
                'status': 'error' if step_2_has_error else ('completed' if has_step_2 else 'pending'),
                'has_prompt': has_step_2,
                'has_results': has_step_2 and not step_2_has_error,
                'has_error': step_2_has_error,
                'error_message': company.llm_research_step_2_strategic.replace('ERROR: ', '') if step_2_has_error else None
            },
            {
                'step': 3,
                'name': 'LLM Report Generation',
                'description': 'Final comprehensive markdown and HTML reports',
                'status': 'error' if step_3_has_error else ('completed' if has_step_3 else 'pending'),
                'has_prompt': has_step_3,
                'has_results': has_step_3 and not step_3_has_error,
                'has_error': step_3_has_error,
                'error_message': company.llm_research_step_3_report.replace('ERROR: ', '') if step_3_has_error else None
            }
        ]

        progress = {
            'success': True,
            'company_id': company_id,
            'company_name': company.company_name,
            'progress_percentage': progress_percentage,
            'steps_completed': steps_completed_count,  # Now a number, not an object
            'total_steps': total_steps,
            'current_step': current_step,
            'current_status': current_status,
            'is_complete': is_complete,
            'step_details': step_details,
            'research_status': status,
            'llm_research_step_status': current_status,
            'llm_research_provider': getattr(company, 'llm_research_provider', ''),
            'llm_research_started_at': getattr(company, 'llm_research_started_at', None),
            'llm_research_completed_at': getattr(company, 'llm_research_completed_at', None),
            'has_html_report': bool(getattr(company, 'llm_html_report', None)) or bool(getattr(company, 'html_report', None))
        }
        
        return jsonify(progress)
        
    except Exception as e:
        current_app.logger.error(f"Error getting LLM step progress for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get step progress: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-step/<step_name>', methods=['GET'])
def get_llm_step_content(company_id, step_name):
    """Get content for a specific LLM research step."""
    try:
        if step_name not in ['step_1', 'step_2', 'step_3']:
            return jsonify({
                'success': False,
                'message': 'Invalid step name. Must be step_1, step_2, or step_3'
            }), 400
        
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        step_titles = {
            'step_1': 'LLM Basic Research',
            'step_2': 'LLM Strategic Analysis',
            'step_3': 'LLM Report Generation'
        }
        
        # Get step content
        step_content = ''
        if step_name == 'step_1':
            step_content = getattr(company, 'llm_research_step_1_basic', '')
        elif step_name == 'step_2':
            step_content = getattr(company, 'llm_research_step_2_strategic', '')
        elif step_name == 'step_3':
            step_content = getattr(company, 'llm_research_step_3_report', '')
        
        # Determine if content is prompt or results
        is_prompt = 'You are an expert B2B go-to-market strategist' in step_content
        content_type = 'prompt' if is_prompt else 'results'
        
        return jsonify({
            'success': True,
            'company_name': company.company_name,
            'step': step_name,
            'step_title': step_titles[step_name],
            'content': step_content,
            'content_type': content_type,
            'has_content': bool(step_content),
            'content_length': len(step_content),
            'word_count': len(step_content.split()) if step_content else 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting LLM step {step_name} content for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get step content: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-report', methods=['GET'])
def get_llm_report(company_id):
    """Get LLM generated reports for a specific company."""
    try:
        report_type = request.args.get('type', 'html')  # html or markdown
        
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        if report_type == 'html':
            report_content = getattr(company, 'llm_html_report', '')
            content_type = 'text/html'
        elif report_type == 'markdown':
            report_content = getattr(company, 'llm_markdown_report', '')
            content_type = 'text/markdown'
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid report type. Use "html" or "markdown"'
            }), 400
        
        if not report_content:
            return jsonify({
                'success': False,
                'message': f'No {report_type} report available for this company. Complete LLM step-by-step research first.'
            }), 404
        
        # For API response, return JSON with report content
        if request.headers.get('Accept') == 'application/json':
            return jsonify({
                'success': True,
                'company_name': company.company_name,
                'report_type': report_type,
                'content': report_content,
                'content_length': len(report_content),
                'llm_research_provider': getattr(company, 'llm_research_provider', ''),
                'llm_research_completed_at': getattr(company, 'llm_research_completed_at', None)
            })
        
        # For direct browser access, return the content directly
        from flask import Response
        return Response(
            report_content,
            mimetype=content_type,
            headers={
                'Content-Disposition': f'inline; filename="{company.company_name}_llm_report.{report_type}"'
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error getting LLM report for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get report: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/delete-reset', methods=['DELETE'])
def delete_and_reset_company(company_id):
    """Reset all deep research data for a single company (keeps company record)."""
    try:
        current_app.logger.info(f"Resetting research data for company {company_id}")
        
        # Get company details before reset for logging
        company = Company.get_by_id(company_id)
        if not company:
            current_app.logger.warning(f"Company {company_id} not found for research reset")
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        company_name = company.company_name
        current_app.logger.info(f"Found company: {company_name} (ID: {company_id})")
        
        # Reset all research data for the company
        success = Company.delete_company(company_id)
        
        if success:
            current_app.logger.info(f"Successfully reset research data for company: {company_name} (ID: {company_id})")
            return jsonify({
                'success': True,
                'message': f'Research data for "{company_name}" reset successfully',
                'company_id': company_id,
                'company_name': company_name
            })
        else:
            current_app.logger.error(f"Failed to reset research for company: {company_name} (ID: {company_id})")
            return jsonify({
                'success': False,
                'message': 'Failed to reset research data - database operation failed'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error resetting research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to reset research data: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-step-results/<int:step_number>', methods=['GET'])
def get_llm_step_results(company_id, step_number):
    """Get results for a specific LLM research step."""
    try:
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Get the appropriate step content
        step_content = None
        step_name = None
        
        if step_number == 1:
            step_content = getattr(company, 'llm_research_step_1_basic', None)
            step_name = 'LLM Basic Research'
        elif step_number == 2:
            step_content = getattr(company, 'llm_research_step_2_strategic', None)
            step_name = 'LLM Strategic Analysis'
        elif step_number == 3:
            step_content = getattr(company, 'llm_research_step_3_report', None)
            step_name = 'LLM Report Generation'
        else:
            return jsonify({
                'success': False,
                'message': f'Invalid step number: {step_number}. Must be 1, 2, or 3.'
            }), 400
        
        if not step_content:
            return jsonify({
                'success': False,
                'message': f'Step {step_number} results not available for {company.company_name}'
            }), 404
        
        # Check if it's an error message
        is_error = step_content.startswith('ERROR:')
        
        return jsonify({
            'success': True,
            'step_number': step_number,
            'step_name': step_name,
            'company_name': company.company_name,
            'content': step_content,
            'is_error': is_error,
            'character_count': len(step_content),
            'word_count': len(step_content.split()) if step_content else 0
        })
        
    except Exception as e:
        app.logger.error(f"Error getting step {step_number} results for company {company_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@company_bp.route('/companies/<int:company_id>/manual-trigger-step-2', methods=['POST'])
def manual_trigger_step_2(company_id):
    """Manually trigger step 2 if step 1 is completed."""
    try:
        from deepresearch.llm_workflow_orchestrator import LLMWorkflowOrchestrator
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        
        # Get OpenAI client from the service
        llm_service = LLMDeepResearchService()
        orchestrator = LLMWorkflowOrchestrator(llm_service.openai_client)
        
        # Trigger step 2
        result = orchestrator.manual_trigger_step_2(company_id)
        
        if result['success']:
            current_app.logger.info(f"Step 2 manually triggered for company {company_id}: {result['message']}")
            return jsonify(result)
        else:
            current_app.logger.warning(f"Failed to trigger step 2 for company {company_id}: {result['error']}")
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error manually triggering step 2 for company {company_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to trigger step 2: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/manual-trigger-step-3', methods=['POST'])
def manual_trigger_step_3(company_id):
    """Manually trigger step 3 if step 2 is completed."""
    try:
        from deepresearch.llm_workflow_orchestrator import LLMWorkflowOrchestrator
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        
        # Get OpenAI client from the service
        llm_service = LLMDeepResearchService()
        orchestrator = LLMWorkflowOrchestrator(llm_service.openai_client)
        
        # Trigger step 3
        result = orchestrator.manual_trigger_step_3(company_id)
        
        if result['success']:
            current_app.logger.info(f"Step 3 manually triggered for company {company_id}: {result['message']}")
            return jsonify(result)
        else:
            current_app.logger.warning(f"Failed to trigger step 3 for company {company_id}: {result['error']}")
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error manually triggering step 3 for company {company_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to trigger step 3: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/step-status', methods=['GET'])
def get_step_status(company_id):
    """Get detailed status of all research steps for a company."""
    try:
        from deepresearch.llm_workflow_orchestrator import LLMWorkflowOrchestrator
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        
        # Get OpenAI client from the service
        llm_service = LLMDeepResearchService()
        orchestrator = LLMWorkflowOrchestrator(llm_service.openai_client)
        
        # Get step status
        result = orchestrator.get_step_status(company_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting step status for company {company_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get step status: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/llm-step-manual-paste', methods=['POST'])
def submit_manual_paste_research(company_id):
    """Submit manually pasted research content for a specific step."""
    try:
        data = request.get_json()
        if not data or 'step' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'message': 'Step and content are required'
            }), 400
        
        step = data['step']
        content = data['content'].strip()
        manual_paste = data.get('manual_paste', True)
        selected_provider = data.get('provider', 'perplexity')  # Default to perplexity if not specified
        
        if step != 1:
            return jsonify({
                'success': False,
                'message': 'Manual paste is only supported for Step 1 Basic Research'
            }), 400
        
        if not content:
            return jsonify({
                'success': False,
                'message': 'Content cannot be empty'
            }), 400
        
        if len(content) < 50:
            return jsonify({
                'success': False,
                'message': 'Content is too short. Please provide comprehensive research content.'
            }), 400
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        current_app.logger.info(f"Manual paste received - Company: {company.company_name}, Provider from request: {selected_provider}, Content length: {len(content)}")
        current_app.logger.info(f"Full request data keys: {list(data.keys()) if data else 'No data'}")
        
        # Store the manual paste content as Step 1 Basic Research
        from deepresearch.database_service import DatabaseService
        from sqlalchemy import text
        
        db_service = DatabaseService()
        
        # Add a prefix to indicate this was manually pasted
        formatted_content = f"[MANUAL PASTE - {len(content)} characters]\n\n{content}"
        
        with db_service.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    UPDATE companies 
                    SET llm_research_step_1_basic = :content,
                        llm_research_step_status = 'step_1_completed_manual',
                        llm_research_provider = 'manual_paste',
                        llm_research_started_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :company_id AND tenant_id = :tenant_id
                """), {
                    'content': formatted_content,
                    'company_id': company_id,
                    'tenant_id': g.tenant_id
                })
        
        current_app.logger.info(f"Successfully stored manual paste research for {company.company_name}")
        
        # Automatically trigger Step 2 and Step 3 after manual paste
        current_app.logger.info(f"Auto-triggering Step 2 and Step 3 for {company.company_name} after manual paste")
        
        try:
            from deepresearch.llm_step_by_step_researcher import LLMStepByStepResearcher
            
            # Initialize the step researcher
            step_researcher = LLMStepByStepResearcher()
            
            # Trigger Step 2 (will automatically continue to Step 3) using selected provider
            auto_result = step_researcher.start_llm_step_research(
                company_id=company_id,
                provider=selected_provider,  # Use the provider selected in the modal
                force_refresh=False  # Don't overwrite the manual paste
            )
            
            if auto_result.get('success'):
                current_app.logger.info(f"✅ Auto-progression initiated successfully for {company.company_name}: {auto_result.get('message', '')}")
                auto_status = 'auto_progression_started'
            else:
                current_app.logger.warning(f"⚠️ Auto-progression failed for {company.company_name}: {auto_result.get('error', '')}")
                auto_status = 'auto_progression_failed'
                
        except Exception as e:
            current_app.logger.error(f"❌ Error during auto-progression for {company.company_name}: {str(e)}")
            auto_status = 'auto_progression_error'
        
        return jsonify({
            'success': True,
            'message': f'Manual research content stored successfully for {company.company_name}. Steps 2 and 3 have been automatically triggered.',
            'company_name': company.company_name,
            'step': step,
            'content_length': len(content),
            'character_count': len(content),
            'word_count': len(content.split()),
            'manual_paste': True,
            'status': 'step_1_completed_manual',
            'auto_progression': auto_status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error submitting manual paste research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to submit manual research: {str(e)}'
        }), 500

@company_bp.route('/companies/<int:company_id>/research-prompt', methods=['GET'])
def get_research_prompt(company_id):
    """Get the basic research prompt for a company to copy for external use."""
    try:
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Generate the research prompt (prompt only, no execution)
        from deepresearch.llm_deep_research_service import LLMDeepResearchService
        
        llm_service = LLMDeepResearchService()
        research_prompt = llm_service.get_research_prompt_only(
            company.company_name, 
            company.website_url or ""
        )
        
        # Validate the prompt
        if not research_prompt or not isinstance(research_prompt, str):
            return jsonify({
                'success': False,
                'message': 'Failed to generate research prompt - invalid prompt returned'
            }), 500
        
        if len(research_prompt.strip()) < 100:
            return jsonify({
                'success': False,
                'message': 'Generated research prompt is too short - please check company data'
            }), 500
        
        current_app.logger.info(f"Generated research prompt for copying for company ID {company_id}: {company.company_name} ({len(research_prompt)} characters)")
        
        return jsonify({
            'success': True,
            'company_id': company_id,
            'company_name': company.company_name,
            'company_website': company.website_url or "",
            'research_prompt': research_prompt,
            'prompt_length': len(research_prompt),
            'word_count': len(research_prompt.split()),
            'generated_at': 'now'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating research prompt for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to generate research prompt: {str(e)}'
        }), 500
