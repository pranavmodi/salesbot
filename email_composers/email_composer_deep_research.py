# email_composer_deep_research.py  ── v1 (research-backed, personalized outreach)

import os, random, textwrap, json, pathlib, time, urllib.parse, requests, hashlib, hmac
from typing import Dict, Tuple, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

import pathlib
_current_dir = pathlib.Path(__file__).parent
PRODUCT_DESC_PATH = str(_current_dir / "productdescription.txt")
PROOF_POINTS_PATH = str(_current_dir / "proofpoints.txt")
DEFAULT_CALENDAR  = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o")
AUTO_RESEARCH     = os.getenv("AUTO_RESEARCH_ENABLED", "true").lower() == "true"
BASE_URL          = os.getenv("BASE_URL", "https://salesbot.possibleminds.in")
NETLIFY_PUBLISH_URL = os.getenv("NETLIFY_PUBLISH_URL", "https://possibleminds.in/.netlify/functions/publish-report-persistent")
NETLIFY_SECRET    = os.getenv("NETLIFY_WEBHOOK_SECRET", "")  # Add this to your .env file

# ---- Context about the sender and product ----
SENDER_INFO = """
Pranav Modi is the founder of Possible Minds and a seasoned product manager and AI engineer.
The team at Possible Minds has developed an AI chatbot product that is deployed in customer support and sales contexts.

The chatbot:
- is trained on the customer's website or docs
- answers queries 24/7 in multiple languages
- integrates easily with existing workflows
- deploys in under 30 minutes
- reduces operational load while improving engagement

It is currently deployed at Precise Imaging, a diagnostic imaging company, where it's helping reduce appointment no-shows and improving patient engagement.
We're in active conversations with several other healthcare and service companies exploring similar use cases.
"""

class DeepResearchEmailComposer:
    """
    Compose research-backed, highly personalized emails using deep company research data.
    Leverages AI research to identify specific pain points and solution hooks.
    """

    def __init__(self) -> None:
        self.client         = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.product_desc   = self._load_text(PRODUCT_DESC_PATH)
        self.proof_points   = self._load_text(PROOF_POINTS_PATH).splitlines()

        self.system_prompt = textwrap.dedent("""
            You're an expert sales strategist writing research-backed, highly personalized cold emails.
            
            You have access to deep company research and should leverage it to create compelling, relevant outreach.
            The email should feel like it was written by someone who deeply understands their business challenges.

            Use this format:
            
            Subject: Create a compelling subject line (≤ 50 characters) that references a specific business challenge or opportunity from the research. Use format: "[Company] → [Specific Outcome/Challenge]?"
            
            Body:
            1. Greeting - "Hi [FirstName]," on its own line
            2. Add a blank line after the greeting
            3. First paragraph (2-3 sentences): Reference a specific business challenge, growth signal, or pain point from the company research. Show you understand their situation. Be specific and credible.
            4. Add a blank line between paragraphs
            5. Second paragraph (2-3 sentences): Brief intro starting with "I'm Pranav, founder of Possible Minds" and connect your AI solution to their specific challenge mentioned above.
            6. Add a blank line
            7. Third paragraph (2-4 bullet points): Specific benefits relevant to their pain points. Use **bold** for key benefits. Reference similar outcomes from your proof points when relevant.
            8. Add a blank line
            9. Fourth paragraph: Direct, specific call to action with calendar link as linked text. Use format like "Worth exploring? <a href="CALENDAR_URL">Let's schedule 15 minutes</a>" instead of showing the full URL.
            10. Add a blank line
            11. Sign-off on its own line (e.g., "Best," - DO NOT include name here, it will be added later)
            12. Add a blank line, then include: "P.S. I put together a strategic analysis for [Company] that covers these opportunities in detail. You can review it here: [REPORT_LINK_PLACEHOLDER]"

            IMPORTANT: 
            - If company research is provided, MUST use specific insights from it
            - If no research available, focus on general industry pain points but still be specific
            - Keep total words ≤ 200 (increased to accommodate report link)
            - Subject MUST start with "Subject:" as the first line
            - Use specific, actionable language
            - Reference real business metrics when possible
            - ALWAYS include the [REPORT_LINK_PLACEHOLDER] in the P.S. section exactly as shown
            - The report link will showcase your deep understanding of their business

            Here is context about the sender and their product:
            """ + SENDER_INFO)

    def compose_email(self, lead: Dict[str, str], calendar_url: str = DEFAULT_CALENDAR, extra_context: str | None = None, auto_research: bool = None, campaign_id: int = None) -> Dict[str, str] | None:
        if not self.product_desc:
            print("❗ productdescription.txt missing – aborting.")
            return None

        first_name = lead.get("name", "").split()[0] if lead.get("name") else "there"
        company_name = lead.get("company", "")
        proof = random.choice(self.proof_points) if self.proof_points else ""

        print(f"\n📧 CAMPAIGN: Starting email composition for {company_name}")

        # Use global setting if auto_research not specified
        if auto_research is None:
            auto_research = AUTO_RESEARCH

        # Try to get company research data (with optional auto-triggering)
        print(f"🔍 DEBUG: Getting research for company: {company_name}")
        company_research, company_id = self._get_company_research_with_full_report(company_name, auto_trigger=auto_research)
        print(f"📋 DEBUG: Research result - company_id: {company_id}, research length: {len(company_research) if company_research else 0}")
        
        # If company_research is None, it means research is in progress but not ready
        if company_research is None:
            print(f"🚫 DEBUG: Research not ready for {company_name} - aborting email composition")
            return None  # Return None to signal email should not be sent
        
        # Generate public report URL with tracking parameters
        report_url = None
        if company_id:
            print(f"🔗 DEBUG: Attempting to get report URL for company_id={company_id}, company_name={company_name}")
            print(f"📧 DEBUG: Campaign ID provided: {campaign_id}, Contact email: {lead.get('email', '')}")
            report_url = self._get_or_publish_report_url(company_id, company_name, lead.get("email", ""), campaign_id)
            print(f"🔗 DEBUG: Generated report_url: {'YES - ' + report_url[:50] + '...' if report_url else 'NO - Empty/None'}")
        else:
            print(f"⚠️ DEBUG: No company_id found, cannot generate report URL")

        user_prompt = f"""
        === Lead ===
        {self._fmt_dict(lead)}

        === First name ===
        {first_name}

        === Company name ===
        {company_name}

        === Product description ===
        {self.product_desc}

        === Proof point (optional) ===
        {proof}

        === Company Research (if available) ===
        {company_research if company_research else "No specific company research available - use general industry insights"}

        === Calendar URL ===
        {calendar_url}

        {extra_context or ''}
        """

        try:
            rsp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.7,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            print(f"🔴 OpenAI email generation failed: {e}")
            return None

        subject, body = self._parse(rsp.choices[0].message.content)
        
        # Replace report link placeholder with HTML linked text
        print(f"🔗 DEBUG: Processing report URL replacement - report_url: {'YES' if report_url else 'NO'}, has placeholder: {'YES' if '[REPORT_LINK_PLACEHOLDER]' in body else 'NO'}")
        
        if report_url and "[REPORT_LINK_PLACEHOLDER]" in body:
            linked_text = f'<a href="{report_url}">strategic analysis report</a>'
            body = body.replace("[REPORT_LINK_PLACEHOLDER]", linked_text)
            print(f"✅ DEBUG: Successfully replaced placeholder with report link")
        elif "[REPORT_LINK_PLACEHOLDER]" in body:
            # If no report URL available, fall back to generic message
            fallback_msg = "Happy to share how we helped Precise Imaging reduce appointment no-shows by 40% - similar healthcare operational challenges."
            body = body.replace("P.S. I put together a strategic analysis for [Company] that covers these opportunities in detail. You can review it here: [REPORT_LINK_PLACEHOLDER]", f"P.S. {fallback_msg}")
            print(f"⚠️ DEBUG: No report URL available, used fallback message")
        else:
            print(f"ℹ️ DEBUG: No placeholder found in email body")
        
        body = body.strip() # Ensure no trailing newlines before adding signature
        body += '\n' + self._signature()
        
        # Convert plain text formatting to HTML for proper email display
        html_body = self._convert_to_html(body)
        
        final_result = {"subject": subject, "body": html_body}
        return final_result

    def _get_or_publish_report_url(self, company_id: int, company_name: str, recipient_email: str, campaign_id: int = None) -> str:
        """Publish report to possibleminds.in and return click tracking URL."""
        try:
            # Import here to avoid circular imports
            from app.models.company import Company
            
            print(f"🔄 DEBUG: _get_or_publish_report_url called with company_id={company_id}, company_name='{company_name}'")
            
            # Get the company data to verify report exists
            company = Company.get_by_id(company_id)
            if not company:
                print(f"❌ DEBUG: Company {company_id} not found in database")
                return ""
            
            print(f"✅ DEBUG: Company {company_id} found in database: {company.company_name}")
            
            # Check if company has markdown_report
            has_markdown = hasattr(company, 'markdown_report') and company.markdown_report
            has_research = hasattr(company, 'company_research') and company.company_research
            print(f"📊 DEBUG: Company data check - has_markdown_report: {has_markdown}, has_company_research: {has_research}")
            
            if not has_markdown:
                print(f"⚠️ DEBUG: Company {company_name} (ID: {company_id}) has no markdown_report")
                print(f"📊 DEBUG: Available fields: company_research={bool(company.company_research)}, research_status={getattr(company, 'research_status', 'unknown')}")
                return ""
            
            print(f"✅ DEBUG: Company {company_name} has markdown_report ({len(company.markdown_report)} chars), proceeding with publishing")
            
            # First, publish the report to possibleminds.in
            print(f"🌐 DEBUG: Attempting to publish report to Netlify...")
            published_url = self._publish_report_to_netlify(company, recipient_email, campaign_id)
            print(f"🌐 DEBUG: Netlify publishing result: {'SUCCESS - ' + published_url[:50] + '...' if published_url else 'FAILED - No URL returned'}")
            
            if published_url:
                # The Netlify function already returns a tracked URL, so we can use it directly
                print(f"✅ DEBUG: Using Netlify published URL as final report URL")
                return published_url
            else:
                # Fallback: generate click tracking URL even if publishing failed
                print(f"🔄 DEBUG: Netlify publishing failed, generating fallback tracking URL...")
                tracked_url = self._generate_report_url_with_tracking(company_id, company_name, recipient_email, campaign_id)
                print(f"🔄 DEBUG: Fallback tracking URL: {'SUCCESS - ' + tracked_url[:50] + '...' if tracked_url else 'FAILED - No URL generated'}")
                return tracked_url
                
        except Exception as e:
            print(f"❌ Error getting/publishing report: {e}")
            return ""

    def _publish_report_to_netlify(self, company, recipient_email: str, campaign_id: int = None) -> str:
        """Publish report to Netlify function and return click tracking URL."""
        try:
            from datetime import datetime
            
            print(f"🌐 DEBUG: Starting Netlify publish for company {company.company_name} (ID: {company.id})")
            print(f"📧 DEBUG: Recipient: {recipient_email}, Campaign: {campaign_id}")
            print(f"📄 DEBUG: Report length: {len(company.markdown_report) if company.markdown_report else 0} chars")
            print(f"🔧 DEBUG: NETLIFY_PUBLISH_URL: {NETLIFY_PUBLISH_URL}")
            print(f"🔐 DEBUG: NETLIFY_SECRET configured: {bool(NETLIFY_SECRET)}")
            
            # Prepare payload for Netlify function
            payload = {
                "company_id": f"comp_{company.id}",
                "company_name": company.company_name,
                "company_website": company.website_url or "",
                "contact_id": f"contact_{recipient_email.split('@')[0]}",
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
                "markdown_report": company.markdown_report
            }
            
            print(f"📦 DEBUG: Payload prepared - company_id: {payload['company_id']}, name: {payload['company_name']}")
            
            # Create payload without the full report for logging
            payload_for_logging = {k: v for k, v in payload.items() if k != 'markdown_report'}
            payload_for_logging['markdown_report'] = f"[{len(payload['markdown_report'])} chars]"
            
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
                print(f"🔐 DEBUG: HMAC signature calculated and added to headers")
            else:
                print(f"⚠️ DEBUG: No NETLIFY_SECRET found - proceeding without signature")
            
            print(f"🌐 DEBUG: Making POST request to {NETLIFY_PUBLISH_URL}")
            headers_safe = {k: v if k != 'X-Hub-Signature-256' else '[HMAC_SIGNATURE]' for k, v in headers.items()}
            print(f"📤 DEBUG: Headers: {headers_safe}")
            print(f"📦 DEBUG: Payload size: {len(raw_body)} bytes")
            
            # Make the request to publish (using raw JSON string)
            response = requests.post(
                NETLIFY_PUBLISH_URL,
                headers=headers,
                data=raw_body,  # Use raw JSON string for signature validation
                timeout=30
            )
            
            print(f"📥 DEBUG: Response status: {response.status_code}")
            print(f"📄 DEBUG: Response content-type: {response.headers.get('content-type', 'unknown')}")
            
            # Only log a small portion of the response to avoid flooding logs
            response_preview = response.text[:200] if response.text else "No response body"
            print(f"📝 DEBUG: Response preview: {response_preview}{'...' if len(response.text) > 200 else ''}")
            
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
                        'utm_campaign': 'deep_research',
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
            
            # Check if we have a published markdown report (full research completed)
            if hasattr(company, 'markdown_report') and company.markdown_report:
                # Use basic research for email context, but we have the full report published
                research_text = company.research_step_1_basic or company.company_research or company.markdown_report[:500] + "..."
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

    def _trigger_company_research(self, company_name: str, company_id: int = None) -> str:
        """Trigger deep research for a company and return basic research if successful."""
        try:
            # Import research services
            from deepresearch.ai_research_service import AIResearchService
            from app.models.company import Company
            
            # If no company_id provided, we need to create the company first
            if company_id is None:
                company_data = {'company_name': company_name, 'website_url': '', 'company_research': ''}
                
                if Company.save(company_data):
                    companies = Company.get_companies_by_name(company_name)
                    if companies:
                        company_id = companies[0].id
                    else:
                        return ""
                else:
                    return ""
            
            # Perform basic research using AI service
            ai_service = AIResearchService()
            research_result = ai_service.research_company(company_name, "")
            
            if research_result:
                Company.update_research_step(company_id, 1, research_result)
                Company.update_research_status(company_id, 'completed')
                return research_result
            else:
                return ""
                
        except Exception as e:
            print(f"❌ Research error for {company_name}: {e}")
            return ""

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
                # Wait for research to complete with polling (max 5 minutes for Railway)
                max_wait_time = 300  # Increased from 60 to 300 seconds (5 minutes)
                poll_interval = 5    # Increased from 3 to 5 seconds to reduce polling frequency
                elapsed_time = 0
                print(f"⏳ DEBUG: Waiting for deep research to complete (max {max_wait_time}s)...")
                
                while elapsed_time < max_wait_time:
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    
                    company = Company.get_by_id(company_id)
                    if company:
                        status = getattr(company, 'research_status', 'unknown')
                        has_markdown = hasattr(company, 'markdown_report') and company.markdown_report
                        has_basic = hasattr(company, 'research_step_1_basic') and company.research_step_1_basic
                        
                        print(f"⏳ DEBUG: Polling {elapsed_time}s/{max_wait_time}s - Status: {status}, Has markdown: {has_markdown}, Has basic: {has_basic}")
                        
                        # Only return when we have BOTH completed status AND markdown_report
                        if status == 'completed' and has_markdown:
                            print(f"✅ DEBUG: Research fully completed with markdown report after {elapsed_time}s")
                            research_text = company.research_step_1_basic or company.company_research or "Research completed - see full report for details."
                            return research_text, company_id
                        elif status == 'failed':
                            print(f"❌ DEBUG: Research failed after {elapsed_time}s")
                            break
                    else:
                        print(f"⚠️ DEBUG: Company {company_id} not found during polling at {elapsed_time}s")
                
                # Timeout or failure - DO NOT send email with placeholder
                print(f"⚠️ DEBUG: Research timeout after {max_wait_time}s - email composition should be delayed")
                company = Company.get_by_id(company_id)
                if company:
                    status = getattr(company, 'research_status', 'unknown')
                    has_markdown = hasattr(company, 'markdown_report') and company.markdown_report
                    print(f"⚠️ DEBUG: Final status check - Status: {status}, Has markdown: {has_markdown}")
                    
                    # If we have basic research but no markdown report, return None to prevent email sending
                    if company.research_step_1_basic and not has_markdown:
                        print(f"🚫 DEBUG: Research in progress but report not ready - preventing email composition")
                        return None, company_id  # Return None to signal "not ready"
                    elif company.research_step_1_basic:
                        research_text = company.research_step_1_basic
                        return research_text, company_id
                    else:
                        return "", company_id
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
                'utm_campaign': 'deep_research',
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

    @staticmethod
    def _load_text(path: str) -> str:
        if not path or not pathlib.Path(path).exists():
            return ""
        return pathlib.Path(path).read_text(encoding="utf-8").strip()

    @staticmethod
    def _fmt_dict(d: Dict[str, str]) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _parse(raw: str) -> Tuple[str, str]:
        """Split the model's response into subject & body, stripping rogue sigs."""
        subj = body = ""
        lines = [l for l in raw.strip().splitlines()]
        
        # Find subject line
        body_start_index = 0
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subj = line.split(":", 1)[1].strip()
                body_start_index = i + 1
                break
        
        # If no subject line found, use default format
        if not subj:
            subj = "[Company] → AI Transformation?"
            body_start_index = 0  # Use all lines for body when no subject found

        # Get all lines after subject as body, preserving empty lines for paragraph spacing
        body_lines = []
        if body_start_index < len(lines):
            stop_phrases = ("warm regards,", "best regards,", "sincerely,", "cheers,", "regards,", "thanks,", "yours,", "kind regards,")
            # Note: "best," is removed from stop_phrases to allow P.S. sections after "Best,"
            
            for line_content in lines[body_start_index:]:
                line_lower = line_content.lower().strip()
                
                # Only check for stop phrases as standalone sign-offs (not within paragraphs)
                # Skip "best," alone as it's often followed by P.S. sections
                if any(line_lower == phrase for phrase in stop_phrases):
                    break
                
                body_lines.append(line_content)
            
            body = '\n'.join(body_lines).strip()
        
        return subj, body

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