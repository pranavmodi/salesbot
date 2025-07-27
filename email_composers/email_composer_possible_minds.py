# email_composer_possible_minds.py  ── v1 (personalized enterprise AI outreach)

import os, pathlib, time, urllib.parse, requests, hashlib, hmac, json
from typing import Dict, Optional, Union

DEFAULT_CALENDAR = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
AUTO_RESEARCH = os.getenv("AUTO_RESEARCH_ENABLED", "true").lower() == "true"
NETLIFY_PUBLISH_URL = os.getenv("NETLIFY_PUBLISH_URL", "https://possibleminds.in/.netlify/functions/publish-report-persistent")
NETLIFY_SECRET = os.getenv("NETLIFY_WEBHOOK_SECRET", "")

class PossibleMindsEmailComposer:
    """
    Compose personalized enterprise AI outreach emails highlighting AI agent strategic value.
    Based on the Possible Minds outreach template with dynamic company and contact personalization.
    Uses template substitution instead of AI generation for consistent messaging.
    """

    def __init__(self) -> None:
        pass

    def compose_email(self, lead: Dict[str, str], calendar_url: str = DEFAULT_CALENDAR, extra_context: Optional[str] = None, auto_research: bool = None, campaign_id: int = None, **kwargs) -> Optional[Dict[str, str]]:
        first_name = lead.get("name", "").split()[0] if lead.get("name") else "there"
        company_name = lead.get("company", "Unknown Company")

        print(f"\n📧 CAMPAIGN: Composing Possible Minds template email for {company_name}")

        # Use global setting if auto_research not specified
        if auto_research is None:
            auto_research = AUTO_RESEARCH

        # Try to get company research data and report URL
        # Always auto-trigger research to ensure we have a report to link to
        company_research, company_id = self._get_company_research_with_full_report(company_name, auto_trigger=True)
        
        # Generate public report URL with tracking parameters
        report_url = None
        if company_id:
            # Wait and retry to ensure report is available
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries and not report_url:
                report_url = self._get_or_publish_report_url(company_id, company_name, lead.get("email", ""), campaign_id)
                if not report_url:
                    print(f"⏳ Report not ready yet for {company_name}, waiting 10 seconds... (attempt {retry_count + 1})")
                    time.sleep(10)
                    retry_count += 1

        # Create subject line
        subject = f"{first_name}, AI momentum at {company_name}?"

        # Create email body using template with report link
        # Always include the link text, even if URL generation fails
        if report_url:
            research_text = f'Our research agent created <a href="{report_url}">this report specifically for you</a> on how Agents can help you achieve your strategic business priorities.'
        else:
            # Fallback with professional message if report URL is not available
            research_text = "Our research agent created a detailed strategic analysis specifically for you on how AI Agents can help you achieve your business priorities. I'd be happy to share it during our call."

        body = f"""Hi {first_name},

I'm the founder of Possible Minds, an AI software company serving enterprises across the globe. We have enabled companies automate customer support, intakes, email routing and responses by building and deploying custom AI agents, helping them improve CSAT scores and save money and time.

I'm curious to know how are you leveraging AI agents at {company_name}? As you may have heard, AI agents are not toys anymore - they accomplish valuable and complex tasks in a predictable, controllable manner with very high accuracy.

Are they a strategic priority at {company_name}? {research_text}

If you find this compelling, I'd be happy to get on a quick <a href="{calendar_url}">15 min call</a> to understand if there are opportunities to collaborate between my team and yours.

Looking forward"""

        # Add signature
        body += '\n' + self._signature()
        
        # Convert to HTML format
        html_body = self._convert_to_html(body)
        
        return {"subject": subject, "body": html_body}

    @staticmethod
    def _convert_to_html(text: str) -> str:
        """Convert plain text email to HTML format while preserving formatting."""
        import re
        
        # Split into lines
        lines = text.split('\n')
        html_lines = []
        
        for line in lines:
            # Skip empty lines for now, we'll add them back as <br> tags
            if not line.strip():
                html_lines.append('<br>')
                continue
                
            # Convert **bold** to <strong>
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            
            # Convert *italic* to <em> 
            line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', line)
            
            # Add the line
            html_lines.append(line)
        
        # Join lines with <br> tags for line breaks
        html_content = '<br>'.join(html_lines)
        
        # Clean up multiple consecutive <br> tags and replace with paragraph breaks
        html_content = re.sub(r'(<br>\s*){3,}', '<br><br>', html_content)
        
        # Wrap in basic HTML structure for better email client compatibility
        html_email = f"""<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    {html_content}
</body>
</html>"""
        
        return html_email

    @staticmethod
    def _signature() -> str:
        """Generate email signature with HTML links."""
        return """
Pranav Modi
Founder, <a href="https://possibleminds.in">Possible Minds</a>
📧 <a href="mailto:pranav@possibleminds.in">pranav@possibleminds.in</a> | 🌐 <a href="https://possibleminds.in">possibleminds.in</a>"""

    def _get_or_publish_report_url(self, company_id: int, company_name: str, recipient_email: str, campaign_id: int = None) -> str:
        """Publish report to possibleminds.in and return click tracking URL."""
        try:
            # Import here to avoid circular imports
            from app.models.company import Company
            
            # Get the company data to verify report exists
            company = Company.get_by_id(company_id)
            if not company or not company.html_report:
                return ""
            
            # First, publish the report to possibleminds.in
            published_url = self._publish_report_to_netlify(company, recipient_email, campaign_id)
            
            if published_url:
                # The Netlify function already returns a tracked URL, so we can use it directly
                return published_url
            else:
                # Fallback: generate click tracking URL even if publishing failed
                tracked_url = self._generate_report_url_with_tracking(company_id, company_name, recipient_email, campaign_id)
                return tracked_url
                
        except Exception as e:
            print(f"❌ Error getting/publishing report: {e}")
            return ""

    def _publish_report_to_netlify(self, company, recipient_email: str, campaign_id: int = None) -> str:
        """Publish report to Netlify function and return click tracking URL."""
        try:
            from datetime import datetime
            
            # Prepare payload for Netlify function
            payload = {
                "company_id": f"comp_{company.id}",
                "company_name": company.company_name,
                "company_website": company.website_url or "",
                "contact_id": f"contact_{recipient_email.split('@')[0]}",
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
                "html_report": company.html_report,
                "pdf_report_base64": company.pdf_report_base64 or ""
            }
            
            raw_body = json.dumps(payload, separators=(',', ':'))
            
            headers = {"Content-Type": "application/json"}
            
            # Calculate HMAC-SHA256 signature if secret is available
            if NETLIFY_SECRET:
                signature = hmac.new(
                    NETLIFY_SECRET.encode('utf-8'),
                    raw_body.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Hub-Signature-256"] = f"sha256={signature}"
            
            # Make the request to publish (using raw JSON string)
            response = requests.post(
                NETLIFY_PUBLISH_URL,
                headers=headers,
                data=raw_body,  # Use raw JSON string for signature validation
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract publishUrl from the nested data structure
                public_url = result.get('data', {}).get('publishUrl') or result.get('public_url')
                
                if public_url:
                    # Extract company slug from the public URL for click tracking
                    import re
                    slug_match = re.search(r'/reports/([^/?]+)', public_url)
                    company_slug = slug_match.group(1) if slug_match else company.company_name.lower().replace(' ', '-').replace('&', 'and')
                    
                    # Create click tracking URL that routes through the tracking function first
                    tracking_params = {
                        'slug': company_slug,
                        'utm_source': 'email',
                        'utm_medium': 'outreach',
                        'utm_campaign': 'possible_minds',
                        'utm_content': 'strategic_analysis',
                        'company': company.company_name.lower().replace(' ', '_'),
                        'recipient': recipient_email.split('@')[0] if recipient_email else 'unknown',
                        'campaign_id': campaign_id if campaign_id else 'unknown'
                    }
                    
                    base_tracking_url = "https://possibleminds.in/.netlify/functions/click-tracking"
                    url_params = urllib.parse.urlencode(tracking_params)
                    tracked_url = f"{base_tracking_url}?{url_params}"
                    
                    return tracked_url
                else:
                    return ""
            else:
                print(f"❌ Report publishing failed (HTTP {response.status_code}): {response.text}")
                return ""
                
        except Exception as e:
            print(f"❌ Report publishing error: {e}")
            return ""

    def _get_company_research_with_full_report(self, company_name: str, auto_trigger: bool = True) -> tuple[str, int]:
        """Get company research data and ensure full report is available. Returns (research_text, company_id)."""
        if not company_name:
            return "", None
            
        try:
            # Import here to avoid circular imports
            from app.models.company import Company
            
            # Try to find company by name
            companies = Company.get_companies_by_name(company_name)
            
            # If company not found and auto-trigger enabled, create company and start research
            if not companies and auto_trigger:
                return self._trigger_full_deep_research(company_name)
            elif not companies:
                return "", None
            
            company = companies[0]  # Take first match
            
            # Check if we have a published HTML report (full research completed)
            if hasattr(company, 'html_report') and company.html_report:
                # Use basic research for email context, but we have the full report published
                research_text = company.research_step_1_basic or company.company_research or "Strategic analysis report available"
                return research_text, company.id
            
            # Check if we have basic research but need full report
            elif hasattr(company, 'research_step_1_basic') and company.research_step_1_basic:
                if auto_trigger:
                    return self._trigger_full_deep_research(company_name, company.id)
                else:
                    return company.research_step_1_basic, company.id
            
            # Check if we have old-style company research but need full report
            elif hasattr(company, 'company_research') and company.company_research:
                if auto_trigger:
                    return self._trigger_full_deep_research(company_name, company.id)
                else:
                    return company.company_research, company.id
            
            else:
                # Company exists but no research data - trigger if auto_trigger enabled
                if auto_trigger:
                    return self._trigger_full_deep_research(company_name, company.id)
                else:
                    return "", company.id
                
        except Exception as e:
            print(f"❌ Error fetching research for {company_name}: {e}")
            return "", None

    def _trigger_full_deep_research(self, company_name: str, company_id: int = None) -> tuple[str, int]:
        """Trigger full step-by-step deep research and return (research_text, company_id)."""
        try:
            # Import research services
            from deepresearch.step_by_step_researcher import StepByStepResearcher
            from app.models.company import Company
            
            # If no company_id provided, we need to create the company first
            if company_id is None:
                company_data = {'company_name': company_name, 'website_url': '', 'company_research': ''}
                
                if Company.save(company_data):
                    companies = Company.get_companies_by_name(company_name)
                    if companies:
                        company_id = companies[0].id
                    else:
                        return "", None
                else:
                    return "", None
            
            # Trigger step-by-step deep research
            researcher = StepByStepResearcher()
            result = researcher.start_deep_research(company_id, force_refresh=False)
            
            if result.get('success'):
                # Wait for research to complete with polling (max 60 seconds)
                max_wait_time = 60
                poll_interval = 3
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    
                    company = Company.get_by_id(company_id)
                    if company and company.research_status == 'completed' and company.html_report:
                        research_text = company.research_step_1_basic or company.company_research or "Research completed - see full report for details."
                        return research_text, company_id
                    elif company and company.research_step_1_basic:
                        return company.research_step_1_basic, company_id
                    elif company and company.research_status == 'failed':
                        break
                
                # Timeout or failure - try to get whatever research is available
                company = Company.get_by_id(company_id)
                if company and (company.research_step_1_basic or company.company_research):
                    research_text = company.research_step_1_basic or company.company_research
                    return research_text, company_id
                else:
                    return "", company_id
            else:
                return "", company_id
                
        except Exception as e:
            print(f"❌ Research error for {company_name}: {e}")
            return "", company_id

    def _generate_report_url_with_tracking(self, company_id: int, company_name: str, recipient_email: str, campaign_id: int = None) -> str:
        """Generate a public report URL with tracking parameters for possibleminds.in."""
        import time
        import uuid
        
        if not company_id:
            return ""
        
        try:
            base_url = "https://possibleminds.in/.netlify/functions/click-tracking"
            company_slug = company_name.lower().replace(' ', '-').replace('&', 'and') if company_name else f"company-{company_id}"
            
            tracking_params = {
                'slug': company_slug,
                'utm_source': 'email',
                'utm_medium': 'outreach',
                'utm_campaign': 'possible_minds',
                'utm_content': 'strategic_analysis',
                'company': company_name if company_name else 'unknown',
                'recipient': recipient_email.split('@')[0] if recipient_email else 'unknown',
                'campaign_id': campaign_id if campaign_id else 'unknown',
                'tracking_id': f"tr_{uuid.uuid4().hex[:8]}",
                'timestamp': int(time.time())
            }
            
            url_params = urllib.parse.urlencode(tracking_params)
            tracked_url = f"{base_url}?{url_params}"
            
            return tracked_url
            
        except Exception as e:
            print(f"❌ Error generating report URL: {e}")
            fallback_url = f"https://possibleminds.in/.netlify/functions/click-tracking?company_id={company_id}&utm_source=email"
            return fallback_url