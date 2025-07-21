from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import json
import threading

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
        description = data.get('description', '')
        email_template = data.get('email_template')
        priority = data.get('priority', 'medium')
        schedule_date = data.get('schedule_date')
        followup_days = data.get('followup_days', 3)
        selection_criteria = data.get('selection_criteria', {})
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
            description=description,
            email_template=email_template,
            priority=priority,
            schedule_date=schedule_date,
            followup_days=followup_days,
            selection_criteria=json.dumps(selection_criteria) # Store as JSON string
        )
        new_campaign.save()
        
        # Associate contacts with the campaign
        campaign_scheduler.associate_contacts_with_campaign(new_campaign.id, target_contacts)
        
        # Schedule the campaign if a schedule date is provided
        if schedule_date:
            campaign_scheduler.schedule_campaign(new_campaign.id, schedule_date)
            
        current_app.logger.info(f"Campaign '{campaign_name}' created and scheduled successfully.")
        
        return jsonify({
            'success': True,
            'message': f'Campaign \'{campaign_name}\' created and scheduled successfully.',
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
    """Get all campaigns."""
    try:
        current_app.logger.info("Loading campaigns...")
        campaigns = Campaign.load_all()
        current_app.logger.info(f"Loaded {len(campaigns)} campaigns")
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
        
        campaign.delete()
        campaign_scheduler.cancel_campaign(campaign_id) # Also cancel any scheduled jobs
        
        return jsonify({'success': True, 'message': 'Campaign deleted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error deleting campaign: {str(e)}")
        return jsonify({'error': 'Failed to delete campaign'}), 500

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
    """Get analytics for a specific campaign."""
    try:
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get email history for this campaign
        campaign_emails = EmailHistory.get_by_campaign_id(campaign_id)
        
        total_sent = len(campaign_emails)
        total_opened = sum(1 for e in campaign_emails if e.status == 'opened')
        total_replied = sum(1 for e in campaign_emails if e.status == 'replied')
        total_bounced = sum(1 for e in campaign_emails if e.status == 'bounced')
        
        # Calculate rates
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
        bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
        
        # Get click data (if available)
        from app.models.report_click import ReportClick
        clicks = ReportClick.get_by_campaign_id(campaign_id)
        total_clicks = len(clicks)
        click_rate = (total_clicks / total_opened * 100) if total_opened > 0 else 0 # Click-through open rate
        
        # Get unique clicks (if needed)
        unique_clicks = len(set(c.contact_email for c in clicks))
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'campaign_name': campaign.name,
            'analytics': {
                'total_sent': total_sent,
                'total_opened': total_opened,
                'total_replied': total_replied,
                'total_bounced': total_bounced,
                'open_rate': round(open_rate, 2),
                'reply_rate': round(reply_rate, 2),
                'bounce_rate': round(bounce_rate, 2),
                'total_clicks': total_clicks,
                'unique_clicks': unique_clicks,
                'click_rate': round(click_rate, 2)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting campaign analytics for campaign {campaign_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve campaign analytics'}), 500

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
            return jsonify({'success': False, 'message': 'Campaign not found'}), 404
        
        # Schedule the campaign for execution
        success = campaign_scheduler.schedule_campaign(campaign_id)
        
        if success:
            current_app.logger.info(f"Campaign {campaign_id} launched successfully")
            return jsonify({
                'success': True,
                'message': f'Campaign "{campaign.name}" launched successfully'
            })
        else:
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

@campaign_bp.route('/campaigns/delete-all', methods=['DELETE'])
def delete_all_campaigns():
    """Delete all campaigns and their associated data."""
    try:
        current_app.logger.info("Deleting all campaigns...")
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
