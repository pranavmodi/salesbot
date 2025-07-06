#!/usr/bin/env python3
"""
Update Campaigns to Deep Research Template
==========================================

This script updates existing campaigns to use the deep_research email template
so they can trigger automatic company research and include published report links.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.campaign import Campaign
from flask import current_app
from app import create_app
import argparse

def list_campaigns():
    """List all campaigns and their current email templates."""
    print("\n📋 Current Campaigns:")
    print("=" * 80)
    
    # Load from both database and JSON
    campaigns = Campaign.load_all()
    
    # Load JSON data
    import json
    import os
    campaigns_json = []
    if os.path.exists('campaigns.json'):
        try:
            with open('campaigns.json', 'r') as f:
                campaigns_json = json.load(f)
        except json.JSONDecodeError:
            print("⚠️  campaigns.json file is corrupted")
    
    if not campaigns and not campaigns_json:
        print("No campaigns found.")
        return
    
    # Display database campaigns
    for campaign in campaigns:
        # Find corresponding JSON entry
        json_entry = None
        for camp in campaigns_json:
            if (str(camp.get('id', '')).endswith(str(campaign.id)) or 
                str(camp.get('id', '')) == str(campaign.id)):
                json_entry = camp
                break
        
        template = json_entry.get('email_template', 'not set') if json_entry else 'not set'
        stats = Campaign.get_campaign_stats(campaign.id)
        
        print(f"ID: {campaign.id}")
        print(f"Name: {campaign.name}")
        print(f"Status: {campaign.status}")
        print(f"Email Template: {template}")
        print(f"Total Contacts: {stats.get('total_contacts', 0)}")
        print(f"Emails Sent: {stats.get('sent_emails', 0)}")
        print("-" * 60)
    
    # Display JSON-only campaigns (if any)
    for camp in campaigns_json:
        camp_id = str(camp.get('id', ''))
        # Check if this campaign is already displayed from database
        found_in_db = False
        for db_campaign in campaigns:
            if (camp_id.endswith(str(db_campaign.id)) or 
                camp_id == str(db_campaign.id)):
                found_in_db = True
                break
        
        if not found_in_db:
            print(f"ID: {camp_id} (JSON only)")
            print(f"Name: {camp.get('name', 'Unknown')}")
            print(f"Status: {camp.get('status', 'unknown')}")
            print(f"Email Template: {camp.get('email_template', 'not set')}")
            print(f"Emails Sent: {camp.get('emails_sent', 0)}")
            print("-" * 60)

def update_campaign_template(campaign_id, template='deep_research'):
    """Update a specific campaign's email template in the JSON file."""
    try:
        import json
        import os
        
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            print(f"❌ Campaign {campaign_id} not found!")
            return False
        
        print(f"\n🔄 Updating Campaign: {campaign.name} (ID: {campaign_id})")
        
        # Load campaigns.json file
        campaigns_file = 'campaigns.json'
        campaigns_data = []
        old_template = 'not set'
        campaign_updated = False
        
        if os.path.exists(campaigns_file):
            try:
                with open(campaigns_file, 'r') as f:
                    campaigns_data = json.load(f)
            except json.JSONDecodeError:
                print("⚠️  campaigns.json file is corrupted, creating new one")
                campaigns_data = []
        
        # Find and update the campaign
        for camp in campaigns_data:
            if (str(camp.get('id', '')).endswith(str(campaign_id)) or 
                str(camp.get('id', '')) == str(campaign_id)):
                old_template = camp.get('email_template', 'not set')
                camp['email_template'] = template
                campaign_updated = True
                print(f"Found campaign {camp.get('id')} in JSON")
                break
        
        # If campaign not found in JSON, create a new entry
        if not campaign_updated:
            new_campaign_entry = {
                'id': f"camp_{campaign_id}",
                'name': campaign.name,
                'type': 'cold_outreach',
                'description': campaign.description or '',
                'email_template': template,
                'priority': 'medium',
                'status': campaign.status,
                'created_at': campaign.created_at.isoformat() if hasattr(campaign.created_at, 'isoformat') else str(campaign.created_at),
                'emails_sent': 0,
                'emails_opened': 0,
                'emails_clicked': 0,
                'responses_received': 0
            }
            campaigns_data.append(new_campaign_entry)
            print(f"Created new JSON entry for campaign {campaign_id}")
            campaign_updated = True
            old_template = 'not set'
        
        print(f"Current template: {old_template}")
        print(f"New template: {template}")
        
        # Save back to file
        if campaign_updated:
            try:
                with open(campaigns_file, 'w') as f:
                    json.dump(campaigns_data, f, indent=2)
                print(f"✅ Successfully updated campaign {campaign_id} to use '{template}' template")
                print(f"📧 New emails will now trigger deep research and include report links!")
                return True
            except Exception as file_error:
                print(f"❌ Error saving campaigns.json: {file_error}")
                return False
        
        return False
        
    except Exception as e:
        print(f"❌ Error updating campaign {campaign_id}: {e}")
        return False

def update_all_campaigns(template='deep_research'):
    """Update all campaigns to use the specified template."""
    campaigns = Campaign.load_all()
    if not campaigns:
        print("No campaigns found.")
        return
    
    print(f"\n🔄 Updating ALL {len(campaigns)} campaigns to use '{template}' template...")
    
    success_count = 0
    for campaign in campaigns:
        if update_campaign_template(campaign.id, template):
            success_count += 1
        print()  # Empty line between campaigns
    
    print(f"🎉 Update Complete: {success_count}/{len(campaigns)} campaigns updated successfully!")

def main():
    parser = argparse.ArgumentParser(description='Update campaigns to use deep research template')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('campaign_id', nargs='?', type=int, help='Campaign ID to update')
    group.add_argument('--list', '-l', action='store_true', help='List all campaigns')
    group.add_argument('--all', '-a', action='store_true', help='Update all campaigns')
    
    parser.add_argument('--template', '-t', default='deep_research', 
                       choices=['deep_research', 'warm', 'alt_subject'],
                       help='Email template to use (default: deep_research)')
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app()
    with app.app_context():
        if args.list:
            list_campaigns()
        elif args.all:
            confirm = input(f"\n⚠️  Are you sure you want to update ALL campaigns to use '{args.template}' template? (yes/no): ")
            if confirm.lower() == 'yes':
                update_all_campaigns(args.template)
            else:
                print("Operation cancelled.")
        else:
            update_campaign_template(args.campaign_id, args.template)

if __name__ == '__main__':
    main() 