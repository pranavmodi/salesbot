from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, timedelta
import json
import threading
from sqlalchemy import text

from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.email_history import EmailHistory
from app.services.campaign_scheduler import campaign_scheduler

campaign_bp = Blueprint('campaign_api', __name__, url_prefix='/api')

@campaign_bp.route('/campaigns', methods=['POST'])
def create_campaign():
    """Create a new GTM campaign with database storage and background processing."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'Campaign name is required'
            }), 400
        
        if not data.get('type'):
            return jsonify({
                'success': False,
                'message': 'Campaign type is required'
            }), 400
        
        if not data.get('email_template'):
            return jsonify({
                'success': False,
                'message': 'Email template is required'
            }), 400
        
        # Get campaign data
        campaign_name = data.get('name')
        campaign_type = data.get('type')
        email_template = data.get('email_template')
        execution_mode = data.get('execution_mode', 'scheduled')
        schedule_date = data.get('schedule_date')
        # Convert empty string to None for database
        if schedule_date == '':
            schedule_date = None
        followup_days = data.get('followup_days', 3)
        
        # Extract campaign settings
        campaign_settings = {
            'execution_mode': execution_mode,
            'email_frequency': data.get('email_frequency', {'value': 30, 'unit': 'minutes'}),
            'random_delay': data.get('random_delay', {'min_minutes': 1, 'max_minutes': 5}),
            'timezone': data.get('timezone', 'America/Los_Angeles'),
            'daily_email_limit': data.get('daily_email_limit', 50),
            'respect_business_hours': data.get('respect_business_hours', True),
            'business_hours': data.get('business_hours', {
                'start_time': '09:00',
                'end_time': '17:00',
                'days': {
                    'monday': True, 'tuesday': True, 'wednesday': True,
                    'thursday': True, 'friday': True, 'saturday': False, 'sunday': False
                }
            })
        }
        
        # Handle both frontend formats: selection_criteria (object) or selection_method (string)
        selection_criteria = data.get('selection_criteria', {})
        selection_method = data.get('selection_method')
        if selection_method and not selection_criteria.get('type'):
            selection_criteria = {'type': selection_method}
            
        selected_contacts = data.get('selected_contacts', [])
        
        # Log campaign creation
        current_app.logger.info(f"Creating database campaign: {campaign_name}")
        current_app.logger.info(f"Campaign type: {campaign_type}")
        current_app.logger.info(f"Selection criteria: {selection_criteria}")
        current_app.logger.info(f"Selected contacts count: {len(selected_contacts)}")
        
        # Get target contacts based on selection criteria (same logic as before)
        target_contacts = []
        if selection_criteria.get('type') == 'manual':
            target_contacts = selected_contacts
        else:
            # For quick and advanced filters, we need to query contacts
            try:
                if selection_criteria.get('type') == 'quick':
                    filter_type = selection_criteria.get('filter_type', 'all')
                    company_filter = selection_criteria.get('company', '')
                    
                    contacts = Contact.load_all()
                    
                    if filter_type == 'uncontacted':
                        # Filter uncontacted contacts
                        uncontacted_emails = EmailHistory.get_uncontacted_emails()
                        target_contacts = [c.to_dict() for c in contacts if c.email in uncontacted_emails]
                    elif filter_type == 'has_phone':
                        target_contacts = [c.to_dict() for c in contacts if c.phone_number]
                    elif filter_type == 'has_linkedin':
                        target_contacts = [c.to_dict() for c in contacts if c.linkedin_url]
                    elif filter_type == 'recent':
                        # Get recently added contacts (last 30 days)
                        thirty_days_ago = datetime.now() - timedelta(days=30)
                        target_contacts = [c.to_dict() for c in contacts if c.created_at and c.created_at >= thirty_days_ago]
                    else:  # 'all'
                        target_contacts = [c.to_dict() for c in contacts]
                    
                    # Apply company filter if specified
                    if company_filter:
                        target_contacts = [c for c in target_contacts if c.get('company', '').lower().find(company_filter.lower()) != -1]
                        
                elif selection_criteria.get('type') == 'advanced':
                    contacts = Contact.load_all()
                    target_contacts = [c.to_dict() for c in contacts]
                    
                    # Apply advanced filters
                    company_contains = selection_criteria.get('company', '').lower()
                    title_contains = selection_criteria.get('job_title', '').lower()
                    location_contains = selection_criteria.get('location', '').lower()
                    
                    if company_contains:
                        target_contacts = [c for c in target_contacts if company_contains in c.get('company', '').lower()]
                    
                    if title_contains:
                        target_contacts = [c for c in target_contacts if title_contains in c.get('job_title', '').lower()]
                    
                    if location_contains:
                        target_contacts = [c for c in target_contacts if location_contains in c.get('location', '').lower()]
                    
                    # Apply boolean filters
                    if selection_criteria.get('exclude_contacted'):
                        uncontacted_emails = EmailHistory.get_uncontacted_emails()
                        target_contacts = [c for c in target_contacts if c.get('email') in uncontacted_emails]
                    
                    if selection_criteria.get('require_phone'):
                        target_contacts = [c for c in target_contacts if c.get('phone_number')]
                    
                    if selection_criteria.get('require_linkedin'):
                        target_contacts = [c for c in target_contacts if c.get('linkedin_url')]
                
            except Exception as filter_error:
                current_app.logger.error(f"Error applying contact filters for campaign: {filter_error}")
                return jsonify({
                    'success': False,
                    'message': f'Error applying contact filters: {filter_error}'
                }), 500

        # Create the campaign in the database
        new_campaign = Campaign(
            name=campaign_name,
            type=campaign_type,
            email_template=email_template,
            schedule_date=schedule_date,
            followup_days=followup_days,
            selection_criteria=json.dumps(selection_criteria), # Store as JSON string
            campaign_settings=json.dumps(campaign_settings) # Store settings as JSON string
        )
        
        # Save campaign and check if successful
        save_success = new_campaign.save()
        if not save_success:
            return jsonify({
                'success': False,
                'message': 'Failed to save campaign to database'
            }), 500
        
        if not new_campaign.id:
            return jsonify({
                'success': False,
                'message': 'Campaign saved but ID not returned'
            }), 500
        
        # Associate contacts with the campaign
        campaign_scheduler.associate_contacts_with_campaign(new_campaign.id, target_contacts)
            
        current_app.logger.info(f"Campaign '{campaign_name}' created successfully as draft with ID {new_campaign.id}")
        
        return jsonify({
            'success': True,
            'message': f'Campaign \'{campaign_name}\' created successfully as draft.',
            'campaign_id': new_campaign.id,
            'contacts_count': len(target_contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating campaign: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to create campaign: {str(e)}'
        }), 500

@campaign_bp.route('/campaigns', methods=['GET'])
def get_campaigns():
    """Get all campaigns with optional execution_mode filter."""
    try:
        current_app.logger.info("Loading campaigns...")
        campaigns = Campaign.load_all()
        current_app.logger.info(f"Loaded {len(campaigns)} campaigns")
        
        # Filter by execution_mode if specified
        execution_mode = request.args.get('execution_mode')
        if execution_mode:
            filtered_campaigns = []
            for campaign in campaigns:
                try:
                    # Parse campaign_settings JSON
                    import json
                    settings = json.loads(campaign.campaign_settings) if campaign.campaign_settings else {}
                    if settings.get('execution_mode') == execution_mode:
                        filtered_campaigns.append(campaign)
                except json.JSONDecodeError:
                    # Skip campaigns with invalid JSON settings
                    continue
            campaigns = filtered_campaigns
            current_app.logger.info(f"Filtered to {len(campaigns)} campaigns with execution_mode={execution_mode}")
        
        campaign_dicts = [campaign.to_dict() for campaign in campaigns]
        current_app.logger.info(f"Converted to {len(campaign_dicts)} campaign dicts")
        return jsonify({'success': True, 'campaigns': campaign_dicts})
    except Exception as e:
        current_app.logger.error(f"Error getting campaigns: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load campaigns'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    """Get a specific campaign by ID."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        return jsonify(campaign.to_dict())
    except Exception as e:
        current_app.logger.error(f"Error getting campaign: {str(e)}")
        return jsonify({'error': 'Failed to load campaign'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>', methods=['PUT'])
def update_campaign(campaign_id):
    """Update an existing campaign."""
    try:
        data = request.get_json()
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Update fields
        campaign.name = data.get('name', campaign.name)
        campaign.type = data.get('type', campaign.type)
        campaign.description = data.get('description', campaign.description)
        campaign.email_template = data.get('email_template', campaign.email_template)
        campaign.priority = data.get('priority', campaign.priority)
        campaign.schedule_date = data.get('schedule_date', campaign.schedule_date)
        campaign.followup_days = data.get('followup_days', campaign.followup_days)
        campaign.selection_criteria = json.dumps(data.get('selection_criteria', json.loads(campaign.selection_criteria)))
        campaign.save()
        
        # Re-associate contacts if selection criteria changed
        if 'selection_criteria' in data:
            selected_contacts = data.get('selected_contacts', [])
            target_contacts = []
            if campaign.selection_criteria_dict.get('type') == 'manual':
                target_contacts = selected_contacts
            else:
                # Re-evaluate filters
                try:
                    if campaign.selection_criteria_dict.get('type') == 'quick':
                        filter_type = campaign.selection_criteria_dict.get('filter_type', 'all')
                        company_filter = campaign.selection_criteria_dict.get('company', '')
                        
                        contacts = Contact.load_all()
                        
                        if filter_type == 'uncontacted':
                            uncontacted_emails = EmailHistory.get_uncontacted_emails()
                            target_contacts = [c.to_dict() for c in contacts if c.email in uncontacted_emails]
                        elif filter_type == 'has_phone':
                            target_contacts = [c.to_dict() for c in contacts if c.phone_number]
                        elif filter_type == 'has_linkedin':
                            target_contacts = [c.to_dict() for c in contacts if c.linkedin_url]
                        elif filter_type == 'recent':
                            thirty_days_ago = datetime.now() - timedelta(days=30)
                            target_contacts = [c.to_dict() for c in contacts if c.created_at and c.created_at >= thirty_days_ago]
                        else:  # 'all'
                            target_contacts = [c.to_dict() for c in contacts]
                        
                        if company_filter:
                            target_contacts = [c for c in target_contacts if c.get('company', '').lower().find(company_filter.lower()) != -1]
                            
                    elif campaign.selection_criteria_dict.get('type') == 'advanced':
                        contacts = Contact.load_all()
                        target_contacts = [c.to_dict() for c in contacts]
                        
                        company_contains = campaign.selection_criteria_dict.get('company', '').lower()
                        title_contains = campaign.selection_criteria_dict.get('job_title', '').lower()
                        location_contains = campaign.selection_criteria_dict.get('location', '').lower()
                        
                        if company_contains:
                            target_contacts = [c for c in target_contacts if company_contains in c.get('company', '').lower()]
                        
                        if title_contains:
                            target_contacts = [c for c in target_contacts if title_contains in c.get('job_title', '').lower()]
                        
                        if location_contains:
                            target_contacts = [c for c in target_contacts if location_contains in c.get('location', '').lower()]
                        
                        if campaign.selection_criteria_dict.get('exclude_contacted'):
                            uncontacted_emails = EmailHistory.get_uncontacted_emails()
                            target_contacts = [c for c in target_contacts if c.get('email') in uncontacted_emails]
                        
                        if campaign.selection_criteria_dict.get('require_phone'):
                            target_contacts = [c for c in target_contacts if c.get('phone_number')]
                        
                        if campaign.selection_criteria_dict.get('require_linkedin'):
                            target_contacts = [c for c in target_contacts if c.get('linkedin_url')]
                
                except Exception as filter_error:
                    current_app.logger.error(f"Error re-evaluating contact filters for campaign update: {filter_error}")
                    return jsonify({
                        'success': False,
                        'message': f'Error re-evaluating contact filters: {filter_error}'
                    }), 500
            
            campaign_scheduler.associate_contacts_with_campaign(campaign.id, target_contacts)
            current_app.logger.info(f"Re-associated {len(target_contacts)} contacts with campaign {campaign.name}")
        
        # Re-schedule if schedule date changed
        if 'schedule_date' in data:
            campaign_scheduler.schedule_campaign(campaign.id, campaign.schedule_date)
            
        return jsonify({'success': True, 'message': 'Campaign updated successfully', 'campaign': campaign.to_dict()})
    except Exception as e:
        current_app.logger.error(f"Error updating campaign: {str(e)}")
        return jsonify({'error': 'Failed to update campaign'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id):
    """Delete a campaign by ID."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        campaign_name = campaign.name  # Store name for logging
        current_app.logger.info(f"Deleting campaign {campaign_id}: {campaign_name}")
        
        # Cancel any scheduled jobs first (this handles campaign_email_jobs)
        campaign_scheduler.cancel_campaign(campaign_id)
        
        # Delete the campaign and all associated data
        success = Campaign.delete(campaign_id)  # Use class method directly
        
        if success:
            current_app.logger.info(f"Successfully deleted campaign {campaign_id}: {campaign_name}")
            return jsonify({'success': True, 'message': f'Campaign "{campaign_name}" deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete campaign from database'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error deleting campaign {campaign_id}: {str(e)}")
        return jsonify({'error': f'Failed to delete campaign: {str(e)}'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/schedule', methods=['POST'])
def schedule_campaign_route(campaign_id):
    """Schedule a campaign to run at a specific time."""
    try:
        data = request.get_json()
        schedule_date_str = data.get('schedule_date')
        
        if not schedule_date_str:
            return jsonify({'success': False, 'message': 'Schedule date is required'}), 400
            
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
            
        campaign_scheduler.schedule_campaign(campaign_id, schedule_date_str)
        
        return jsonify({'success': True, 'message': f'Campaign {campaign.name} scheduled for {schedule_date_str}'})
    except Exception as e:
        current_app.logger.error(f"Error scheduling campaign: {str(e)}")
        return jsonify({'error': 'Failed to schedule campaign'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/analytics', methods=['GET'])
def get_campaign_analytics(campaign_id):
    """Get analytics for a specific campaign from external PossibleMinds endpoint."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Import PossibleMinds analytics service
        from app.services.possibleminds_analytics_service import create_possibleminds_service
        
        # Get analytics from PossibleMinds endpoint
        current_app.logger.info(f"Fetching analytics for campaign {campaign_id} from PossibleMinds")
        analytics_service = create_possibleminds_service()
        analytics_data = analytics_service.get_campaign_clicks(str(campaign_id))
        
        if not analytics_data.get('success', True):
            current_app.logger.warning(f"PossibleMinds analytics warning for campaign {campaign_id}: {analytics_data.get('message')}")
            # Return empty analytics rather than failing
            analytics_data = {
                'success': True,
                'clicks': [],
                'total_clicks': 0,
                'unique_visitors': 0,
                'message': 'No analytics data available'
            }
        
        # Extract metrics from PossibleMinds response
        clicks = analytics_data.get('clicks', [])
        total_clicks = analytics_data.get('total_clicks', len(clicks))
        unique_visitors = analytics_data.get('unique_visitors', 0)
        
        # Calculate additional metrics if available
        unique_emails = len(set(click.get('contact_email', '') for click in clicks if click.get('contact_email')))
        
        # Get campaign statistics (email counts, etc.)
        campaign_stats = Campaign.get_campaign_stats(campaign_id)
        current_app.logger.info(f"Campaign stats for {campaign_id}: {campaign_stats}")
        
        # Calculate click rate if we have email data
        click_rate = 0
        if campaign_stats.get('sent_emails', 0) > 0:
            click_rate = round((total_clicks / campaign_stats['sent_emails'] * 100), 2)
        
        current_app.logger.info(f"Campaign {campaign_id} analytics: {total_clicks} clicks, {unique_visitors} unique visitors, {campaign_stats.get('sent_emails', 0)} emails sent")
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'campaign_name': campaign.name,
            'performance_metrics': {
                'total_contacts': campaign_stats.get('total_contacts', 0),
                'total_emails': campaign_stats.get('sent_emails', 0),  # Use sent_emails for "emails sent" metric
                'total_clicks': total_clicks,
                'unique_recipients': campaign_stats.get('unique_recipients', 0),
                'click_rate': f"{click_rate}%" if click_rate > 0 else "0%",
                'success_rate': campaign_stats.get('success_rate', 0)
            },
            'analytics': {
                'total_clicks': total_clicks,
                'unique_clicks': unique_emails,
                'unique_visitors': unique_visitors,
                'unique_recipients': unique_emails,
                'click_rate': f"{click_rate}%" if click_rate > 0 else "0%",
                'source': 'possibleminds',
                'raw_data': analytics_data,
                'companies_clicked': list(set(click.get('company_name', 'Unknown') for click in clicks if click.get('company_name')))
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting campaign analytics for campaign {campaign_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve campaign analytics'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/schedule', methods=['GET'])
def get_campaign_schedule(campaign_id):
    """Get execution schedule for a specific campaign including pending and sent emails."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Get campaign settings for display
        campaign_settings = {}
        if hasattr(campaign, 'campaign_settings') and campaign.campaign_settings:
            try:
                import json
                campaign_settings = json.loads(campaign.campaign_settings) if isinstance(campaign.campaign_settings, str) else campaign.campaign_settings
            except:
                campaign_settings = {}
        
        # Get pending emails for this campaign
        pending_emails = []
        try:
            from app.models.campaign_email_job import CampaignEmailJob
            from app.database import get_shared_engine
            from sqlalchemy import text
            
            engine = get_shared_engine()
            if engine:
                
                with engine.connect() as conn:
                    # Get pending email jobs for this campaign
                    pending_query = text("""
                        SELECT id, campaign_id, contact_email, scheduled_time, status, attempts, error_message
                        FROM campaign_email_jobs 
                        WHERE campaign_id = :campaign_id 
                        AND status IN ('pending', 'scheduled')
                        AND tenant_id = :tenant_id
                        ORDER BY scheduled_time ASC
                        LIMIT 100
                    """)
                    
                    result = conn.execute(pending_query, {"campaign_id": campaign_id, "tenant_id": g.tenant_id})
                    pending_rows = result.fetchall()
                    
                    for row in pending_rows:
                        pending_emails.append({
                            'id': row.id,
                            'campaign_id': row.campaign_id,
                            'contact_email': row.contact_email,
                            'scheduled_time': row.scheduled_time.isoformat() if row.scheduled_time else None,
                            'status': row.status,
                            'attempts': row.attempts or 0,
                            'error_message': row.error_message
                        })
                        
        except Exception as e:
            current_app.logger.error(f"Error getting pending emails for campaign {campaign_id}: {e}")
        
        # Get recent sent emails for this campaign
        sent_emails = []
        try:
            from app.models.email_history import EmailHistory
            
            # Get recent emails sent for this campaign
            email_history = EmailHistory.get_by_campaign_id(campaign_id)
            
            # Convert to list and get most recent 50
            recent_emails = sorted(email_history, key=lambda x: x.date or '', reverse=True)[:50]
            
            for email in recent_emails:
                sent_emails.append({
                    'id': email.id,
                    'to': email.to,
                    'contact_email': email.to,
                    'subject': email.subject,
                    'date': email.date.isoformat() if email.date else None,
                    'sent_time': email.date.isoformat() if email.date else None,
                    'status': email.status,
                    'campaign_id': email.campaign_id,
                    'sent_via': getattr(email, 'sent_via', 'unknown'),
                    'email_type': getattr(email, 'email_type', 'campaign')
                })
                
        except Exception as e:
            current_app.logger.error(f"Error getting sent emails for campaign {campaign_id}: {e}")
        
        # Get campaign statistics
        stats = {}
        try:
            campaign_stats = Campaign.get_campaign_stats(campaign_id)
            stats = {
                'total_contacts': campaign_stats.get('total_contacts', 0),
                'emails_sent': campaign_stats.get('sent_emails', 0),
                'pending_emails': len(pending_emails),
                'unique_recipients': campaign_stats.get('unique_recipients', 0),
                'success_rate': campaign_stats.get('success_rate', 0)
            }
        except Exception as e:
            current_app.logger.error(f"Error getting campaign stats for {campaign_id}: {e}")
            stats = {
                'total_contacts': 0,
                'emails_sent': len(sent_emails),
                'pending_emails': len(pending_emails),
                'unique_recipients': 0,
                'success_rate': 0
            }
        
        # Get contacts data for manual campaigns
        contacts_data = []
        execution_mode = campaign_settings.get('execution_mode', 'scheduled')
        
        if execution_mode == 'manual':
            try:
                # Get campaign contacts for manual campaigns
                campaign_contacts = Campaign.get_campaign_contacts(campaign_id)
                
                for cc in campaign_contacts:
                    contact_data = {
                        'id': cc.get('id') or cc.get('company_id'),
                        'lead_id': cc.get('id') or cc.get('company_id'),
                        'name': cc.get('full_name') or cc.get('first_name', 'Unknown'),
                        'email': cc.get('email', 'No email'),
                        'company_name': cc.get('company_name', 'Unknown Company'),
                        'position': cc.get('job_title', 'Unknown Position'),
                        'status': cc.get('campaign_status', 'active'),
                        'created_at': cc.get('added_at'),
                        'updated_at': cc.get('status_updated_at')
                    }
                    contacts_data.append(contact_data)
                    
            except Exception as e:
                current_app.logger.error(f"Error getting contacts for manual campaign {campaign_id}: {e}")
        
        # Format campaign data for frontend
        campaign_data = {
            'id': campaign.id,
            'name': campaign.name,
            'status': campaign.status,
            'type': campaign.type,
            'execution_mode': execution_mode,
            'daily_email_limit': campaign_settings.get('daily_email_limit', 50),
            'email_frequency': campaign_settings.get('email_frequency', {'value': 30, 'unit': 'minutes'}),
            'timezone': campaign_settings.get('timezone', 'UTC'),
            'respect_business_hours': campaign_settings.get('respect_business_hours', True),
            'business_hours': campaign_settings.get('business_hours', {}),
            'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
            'updated_at': campaign.updated_at.isoformat() if campaign.updated_at else None
        }
        
        current_app.logger.info(f"Schedule data for campaign {campaign_id} ({execution_mode}): {len(pending_emails)} pending, {len(sent_emails)} sent, {len(contacts_data)} contacts")
        
        return jsonify({
            'success': True,
            'campaign': campaign_data,
            'pending_emails': pending_emails,
            'sent_emails': sent_emails,
            'contacts': contacts_data,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting campaign schedule for campaign {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to retrieve campaign schedule'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/status', methods=['GET'])
def get_campaign_status(campaign_id):
    """Get the current status and basic stats of a campaign."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        stats = Campaign.get_campaign_stats(campaign_id)
        
        return jsonify({
            'success': True,
            'campaign_id': campaign.id,
            'status': campaign.status,
            'stats': stats
        })
    except Exception as e:
        current_app.logger.error(f"Error getting campaign status for {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve campaign status'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/activity', methods=['GET'])
def get_campaign_activity(campaign_id):
    """Get recent activity (emails sent) for a specific campaign."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        # Get recent email history for this campaign (e.g., last 20)
        recent_emails = EmailHistory.get_by_campaign_id(campaign_id, limit=20)
        
        activity_data = []
        for email in recent_emails:
            activity_data.append({
                'id': email.id,
                'to': email.to,
                'subject': email.subject,
                'status': email.status,
                'date': email.date.isoformat() if email.date else None,
                'direction': 'sent' # Campaign activity emails are always 'sent'
            })
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'activity': activity_data
        })
    except Exception as e:
        current_app.logger.error(f"Error getting campaign activity for {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve campaign activity'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/execute-now', methods=['POST'])
def execute_campaign_now(campaign_id):
    """Execute a campaign immediately (test mode)."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        current_app.logger.info(f"Executing campaign {campaign_id} immediately (test mode)")
        
        # Import the test mode execution function
        from app.services.campaign_scheduler import execute_campaign_job_test_mode
        
        # Execute in a thread to avoid blocking the response
        import threading
        execution_thread = threading.Thread(
            target=execute_campaign_job_test_mode, 
            args=[campaign_id]
        )
        execution_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Campaign "{campaign.name}" execution started immediately (test mode)'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error executing campaign immediately: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to execute campaign: {str(e)}'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/launch', methods=['POST'])
def launch_campaign(campaign_id):
    """Launch a campaign for scheduled execution."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            current_app.logger.error(f"🚀 DEBUG: Campaign {campaign_id} not found during launch")
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        current_app.logger.info(f"🚀 DEBUG: Launching campaign {campaign_id} ('{campaign.name}') - current status: {campaign.status}")
        
        # Check if campaign has contacts
        contacts = Campaign.get_campaign_contacts(campaign_id, status='active')
        current_app.logger.info(f"👥 DEBUG: Campaign {campaign_id} has {len(contacts) if contacts else 0} active contacts")
        
        if not contacts:
            current_app.logger.warning(f"⚠️ DEBUG: Campaign {campaign_id} has no contacts - cannot launch")
            return jsonify({
                'success': False,
                'message': 'Cannot launch campaign: No contacts associated with this campaign'
            }), 400
        
        # Schedule the campaign for execution
        current_app.logger.info(f"📅 DEBUG: Scheduling campaign {campaign_id} for execution")
        success = campaign_scheduler.schedule_campaign(campaign_id)
        
        if success:
            current_app.logger.info(f"✅ DEBUG: Campaign {campaign_id} launched successfully")
            return jsonify({
                'success': True,
                'message': f'Campaign "{campaign.name}" launched successfully'
            })
        else:
            current_app.logger.error(f"❌ DEBUG: Failed to schedule campaign {campaign_id}")
            return jsonify({
                'success': False,
                'message': 'Failed to launch campaign'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error launching campaign: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to launch campaign: {str(e)}'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/pause', methods=['POST'])
def pause_campaign(campaign_id):
    """Pause a running campaign."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        success = campaign_scheduler.pause_campaign(campaign_id)
        
        if success:
            current_app.logger.info(f"Campaign {campaign_id} paused successfully")
            return jsonify({
                'success': True,
                'message': f'Campaign "{campaign.name}" paused successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to pause campaign'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error pausing campaign: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to pause campaign: {str(e)}'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/resume', methods=['POST'])
def resume_campaign(campaign_id):
    """Resume a paused campaign."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        success = campaign_scheduler.resume_campaign(campaign_id)
        
        if success:
            current_app.logger.info(f"Campaign {campaign_id} resumed successfully")
            return jsonify({
                'success': True,
                'message': f'Campaign "{campaign.name}" resumed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to resume campaign'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error resuming campaign: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to resume campaign: {str(e)}'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/reset', methods=['POST'])
def reset_campaign_for_testing(campaign_id):
    """Reset a campaign for testing - sets all contacts back to 'active' status."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        current_app.logger.info(f"Resetting campaign {campaign_id} for testing")
        
        # Get current stats before reset
        stats_before = Campaign.get_campaign_stats(campaign_id)
        
        # Reset all contacts to 'active' status
        contacts = Campaign.get_campaign_contacts(campaign_id)
        reset_count = 0
        
        for contact in contacts:
            if contact.get('campaign_status') != 'active':
                success = Campaign.update_contact_status_in_campaign(
                    campaign_id, contact['email'], 'active'
                )
                if success:
                    reset_count += 1
                    current_app.logger.debug(f"Reset {contact['email']} to active")
        
        # Reset campaign status to 'ready'
        Campaign.update_status(campaign_id, 'ready')
        
        # Get new stats after reset
        stats_after = Campaign.get_campaign_stats(campaign_id)
        
        current_app.logger.info(f"Campaign {campaign_id} reset completed: {reset_count} contacts reset")
        
        return jsonify({
            'success': True,
            'message': f'Campaign "{campaign.name}" reset for testing: {reset_count} contacts reset to active',
            'reset_count': reset_count,
            'stats_before': stats_before,
            'stats_after': stats_after
        })
        
    except Exception as e:
        current_app.logger.error(f"Error resetting campaign {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to reset campaign: {str(e)}'}), 500

@campaign_bp.route('/campaigns/delete-all', methods=['DELETE'])
def delete_all_campaigns():
    """Delete all campaigns and their associated data."""
    try:
        current_app.logger.info("Deleting all campaigns...")
        
        # Log pending emails before deletion
        from app.models.campaign_email_job import CampaignEmailJob
        from app.database import get_shared_engine
        from sqlalchemy import text
        
        engine = get_shared_engine()
        if engine:
            try:
                with engine.connect() as conn:
                    # Get all pending email jobs with campaign info
                    pending_jobs_query = text("""
                        SELECT cej.campaign_id, cej.contact_email, cej.scheduled_time, c.name as campaign_name
                        FROM campaign_email_jobs cej
                        JOIN campaigns c ON cej.campaign_id = c.id
                        WHERE cej.status = 'pending'
                        AND cej.tenant_id = :tenant_id
                        AND c.tenant_id = :tenant_id
                        ORDER BY cej.scheduled_time ASC
                    """)
                    
                    result = conn.execute(pending_jobs_query, {"tenant_id": g.tenant_id})
                    pending_jobs = result.fetchall()
                    
                    if pending_jobs:
                        current_app.logger.warning(f"🚨 DELETING {len(pending_jobs)} PENDING EMAILS:")
                        
                        # Group by campaign for cleaner logging
                        campaigns_with_pending = {}
                        for job in pending_jobs:
                            campaign_name = job.campaign_name
                            if campaign_name not in campaigns_with_pending:
                                campaigns_with_pending[campaign_name] = []
                            campaigns_with_pending[campaign_name].append({
                                'email': job.contact_email,
                                'scheduled': job.scheduled_time
                            })
                        
                        for campaign_name, emails in campaigns_with_pending.items():
                            current_app.logger.warning(f"📧 Campaign '{campaign_name}': {len(emails)} pending emails")
                            for email_info in emails[:3]:  # Show first 3 emails
                                current_app.logger.warning(f"   • {email_info['email']} (scheduled: {email_info['scheduled']})")
                            if len(emails) > 3:
                                current_app.logger.warning(f"   • ... and {len(emails) - 3} more")
                    else:
                        current_app.logger.info("✅ No pending emails to cancel")
                        
            except Exception as e:
                current_app.logger.error(f"Error checking pending emails: {e}")
        
        result = Campaign.delete_all_campaigns()
        
        current_app.logger.info(f"Delete all campaigns result: {result}")
        
        return jsonify({
            'success': True,
            'message': 'All campaigns deleted successfully',
            'deleted_counts': result
        })
    except Exception as e:
        current_app.logger.error(f"Error deleting all campaigns: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to delete campaigns: {str(e)}'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/duplicate', methods=['POST'])
def duplicate_campaign(campaign_id):
    """Duplicate an existing campaign with all its settings and contacts."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        current_app.logger.info(f"Duplicating campaign {campaign_id}")
        
        # Get campaign settings
        campaign_settings = {}
        if hasattr(campaign, 'campaign_settings') and campaign.campaign_settings:
            try:
                campaign_settings = json.loads(campaign.campaign_settings) if isinstance(campaign.campaign_settings, str) else campaign.campaign_settings
            except:
                campaign_settings = {}
        
        # Create duplicate campaign with modified name
        duplicate_name = f"{campaign.name} (Copy)"
        
        # Check if name already exists and increment if needed
        existing_campaigns = Campaign.get_all_campaigns()
        existing_names = [c.name for c in existing_campaigns]
        counter = 1
        while duplicate_name in existing_names:
            duplicate_name = f"{campaign.name} (Copy {counter})"
            counter += 1
        
        # Create new campaign
        new_campaign = Campaign(
            name=duplicate_name,
            type=campaign.type,
            email_template=getattr(campaign, 'email_template', 'warm'),
            status='draft',
            campaign_settings=json.dumps(campaign_settings) if campaign_settings else None,
            followup_days=getattr(campaign, 'followup_days', 3),
            schedule_date=None  # Reset schedule date for copy
        )
        
        if new_campaign.save():
            new_campaign_id = new_campaign.id
            current_app.logger.info(f"Created duplicate campaign {new_campaign_id} with name '{duplicate_name}'")
            
            # Copy campaign contacts
            try:
                original_contacts = Campaign.get_campaign_contacts(campaign_id)
                if original_contacts:
                    contact_emails = [contact['email'] for contact in original_contacts]
                    result = Campaign.bulk_add_contacts_to_campaign(new_campaign_id, contact_emails, status='active')
                    current_app.logger.info(f"Copied {result['success']} contacts to duplicate campaign")
                else:
                    current_app.logger.info("No contacts to copy from original campaign")
            except Exception as e:
                current_app.logger.error(f"Error copying contacts to duplicate campaign: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Campaign duplicated successfully as "{duplicate_name}"',
                'new_campaign_id': new_campaign_id,
                'new_campaign_name': duplicate_name
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create duplicate campaign'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error duplicating campaign {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to duplicate campaign: {str(e)}'}), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/contact/<int:contact_id>/status', methods=['GET'])
def get_contact_campaign_status(campaign_id, contact_id):
    """Check if a contact is in a campaign and if email has been sent."""
    try:
        # Check if campaign exists
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({
                'success': False,
                'message': 'Campaign not found'
            }), 404
            
        # Check if contact is part of the campaign
        from app.models.campaign_contact import CampaignContact
        campaign_contact = CampaignContact.get_by_campaign_and_contact(campaign_id, contact_id)
        
        if not campaign_contact:
            return jsonify({
                'success': True,
                'in_campaign': False,
                'email_sent': False,
                'last_email_date': None
            })
        
        # Check if email has been sent for this campaign contact
        email_sent = campaign_contact.status in ['email_sent', 'responded', 'completed']
        last_email_date = None
        
        if hasattr(campaign_contact, 'last_email_sent_at') and campaign_contact.last_email_sent_at:
            last_email_date = campaign_contact.last_email_sent_at.strftime('%Y-%m-%d %H:%M')
        
        return jsonify({
            'success': True,
            'in_campaign': True,
            'email_sent': email_sent,
            'last_email_date': last_email_date,
            'contact_status': campaign_contact.status,
            'campaign_name': campaign.name
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking contact campaign status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error checking status: {str(e)}'
        }), 500

@campaign_bp.route('/campaigns/<int:campaign_id>/contacts', methods=['GET'])
def get_campaign_contacts(campaign_id):
    """Get all contacts associated with a campaign."""
    try:
        # Get campaign
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({
                'success': False,
                'message': 'Campaign not found'
            }), 404
        
        # Get campaign contacts using existing method
        campaign_contacts = Campaign.get_campaign_contacts(campaign_id)
        
        # Format contacts for frontend
        contacts = []
        for cc in campaign_contacts:
            contact_data = {
                'id': cc.get('id') or cc.get('company_id'),
                'lead_id': cc.get('id') or cc.get('company_id'), # Use contact ID as lead_id for compatibility
                'campaign_id': campaign_id,
                'status': cc.get('campaign_status', 'active'),
                'name': cc.get('full_name') or cc.get('first_name', 'Unknown'),
                'email': cc.get('email', 'No email'),
                'company_name': cc.get('company_name', 'Unknown Company'),
                'position': cc.get('job_title', 'Unknown Position'),
                'created_at': cc.get('added_at'),
                'updated_at': cc.get('status_updated_at')
            }
            
            # Get last email date from email history for this contact
            try:
                # Query email history directly to get last email
                from app.database import get_shared_engine
                engine = get_shared_engine()
                with engine.connect() as conn:
                    last_email_query = text("""
                        SELECT sent_at FROM email_history 
                        WHERE campaign_id = :campaign_id 
                        AND recipient_email = :email
                        AND tenant_id = :tenant_id
                        ORDER BY sent_at DESC 
                        LIMIT 1
                    """)
                    last_email_result = conn.execute(last_email_query, {
                        'campaign_id': campaign_id,
                        'email': cc.get('email'),
                        'tenant_id': g.tenant_id
                    })
                    last_email_row = last_email_result.fetchone()
                    
                    if last_email_row:
                        contact_data['last_email_date'] = last_email_row[0].isoformat() if last_email_row[0] else None
                    else:
                        contact_data['last_email_date'] = None
            except Exception as e:
                current_app.logger.warning(f"Could not get last email date for contact {cc.get('email')}: {e}")
                contact_data['last_email_date'] = None
            
            contacts.append(contact_data)
        
        return jsonify({
            'success': True,
            'contacts': contacts,
            'count': len(contacts),
            'campaign_id': campaign_id,
            'campaign_name': campaign.name
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching campaign contacts: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching contacts: {str(e)}'
        }), 500
