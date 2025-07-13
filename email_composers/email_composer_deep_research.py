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
NETLIFY_PUBLISH_URL = "https://possibleminds.in/.netlify/functions/publish-report-persistent"
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
        self.client         = OpenAI(api_key=os.getenv("OPENAI_KEY"))
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
            9. Fourth paragraph: Direct, specific call to action with calendar link. Reference exploring their specific challenge/opportunity.
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
        print(f"🔍 DEBUG: Lead data: {lead}")

        # Use global setting if auto_research not specified
        if auto_research is None:
            auto_research = AUTO_RESEARCH

        print(f"🔍 DEBUG: Auto-research enabled: {auto_research}")
        
        # Progress logging for UI
        if company_name:
            print(f"📊 PROGRESS: Looking up company research for {company_name}")
        else:
            print(f"⚠️ PROGRESS: No company name provided, using generic template")

        # Try to get company research data (with optional auto-triggering)
        company_research, company_id = self._get_company_research_with_full_report(company_name, auto_trigger=auto_research)
        
        print(f"🔍 DEBUG: Research result - Company ID: {company_id}, Research length: {len(company_research) if company_research else 0}")
        
        # Progress logging for research result
        if company_research:
            print(f"✅ PROGRESS: Found company research data for {company_name}")
        else:
            print(f"⚠️ PROGRESS: No research data found, using generic insights")
        
        # Generate public report URL with tracking parameters
        report_url = None
        if company_id:
            print(f"📊 PROGRESS: Publishing strategic report to possibleminds.in for {company_name}")
            report_url = self._get_or_publish_report_url(company_id, company_name, lead.get("email", ""), campaign_id)
            if report_url:
                print(f"✅ PROGRESS: Strategic report published and tracking URL ready")
                print(f"🔍 DEBUG: Generated report URL: {report_url}")
            else:
                print(f"⚠️ PROGRESS: Report publishing failed, using fallback message")
        else:
            print(f"🔍 DEBUG: No company ID available, skipping report URL generation")

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
            print(f"🤖 PROGRESS: Generating personalized email content for {company_name}")
            print(f"🔍 DEBUG: Using OpenAI model: {OPENAI_MODEL}")
            rsp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.7,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            print(f"✅ PROGRESS: Email content generated successfully")
        except Exception as e:
            print(f"🔴 PROGRESS: OpenAI email generation failed: {e}")
            return None

        subject, body = self._parse(rsp.choices[0].message.content)
        
        print(f"🔍 DEBUG: Email body before placeholder replacement:")
        print(f"🔍 DEBUG: Contains placeholder: {'[REPORT_LINK_PLACEHOLDER]' in body}")
        print(f"🔍 DEBUG: Report URL available: {report_url is not None}")
        
        # Replace report link placeholder with actual URL
        if report_url and "[REPORT_LINK_PLACEHOLDER]" in body:
            print(f"🔗 PROGRESS: Embedding strategic report link in email")
            body = body.replace("[REPORT_LINK_PLACEHOLDER]", report_url)
            print(f"✅ PROGRESS: Strategic report link embedded successfully")
        elif "[REPORT_LINK_PLACEHOLDER]" in body:
            print(f"⚠️ PROGRESS: No report URL available, using proof point fallback")
            # If no report URL available, fall back to generic message
            fallback_msg = "Happy to share how we helped Precise Imaging reduce appointment no-shows by 40% - similar healthcare operational challenges."
            body = body.replace("P.S. I put together a strategic analysis for [Company] that covers these opportunities in detail. You can review it here: [REPORT_LINK_PLACEHOLDER]", f"P.S. {fallback_msg}")
            print(f"✅ PROGRESS: Fallback message applied successfully")
        else:
            print(f"🔍 DEBUG: No placeholder found in email body")
        
        body = body.strip() # Ensure no trailing newlines before adding signature
        body += '\n\n' + self._signature()
        
        final_result = {"subject": subject, "body": body}
        print(f"🎉 PROGRESS: Email composition completed for {company_name}")
        print(f"📧 PROGRESS: Final email ready for delivery")
        return final_result

    def _get_or_publish_report_url(self, company_id: int, company_name: str, recipient_email: str, campaign_id: int = None) -> str:
        """Publish report to possibleminds.in and return click tracking URL."""
        print(f"🔍 DEBUG: Getting/publishing report for company_id: {company_id}")
        
        try:
            # Import here to avoid circular imports
            from app.models.company import Company
            
            # Get the company data to verify report exists
            company = Company.get_by_id(company_id)
            if not company or not company.markdown_report:
                print(f"🔍 DEBUG: No markdown report available for company_id: {company_id}")
                return ""
            
            print(f"🔍 DEBUG: Found markdown report, publishing to possibleminds.in...")
            
            # First, publish the report to possibleminds.in
            published_url = self._publish_report_to_netlify(company, recipient_email)
            
            if published_url:
                print(f"🔍 DEBUG: Successfully published report, URL: {published_url}")
                # The Netlify function already returns a tracked URL, so we can use it directly
                return published_url
            else:
                print(f"🔍 DEBUG: Failed to publish report, using fallback tracking URL")
                # Fallback: generate click tracking URL even if publishing failed
                tracked_url = self._generate_report_url_with_tracking(company_id, company_name, recipient_email, campaign_id)
                return tracked_url
                
        except Exception as e:
            print(f"❌ Error getting/publishing report: {e}")
            return ""

    def _publish_report_to_netlify(self, company, recipient_email: str) -> str:
        """Publish report to Netlify function and return public URL."""
        try:
            from datetime import datetime
            
            print(f"📊 PROGRESS: Preparing strategic report for publication")
            
            # Prepare payload for Netlify function
            payload = {
                "company_id": f"comp_{company.id}",
                "company_name": company.company_name,
                "company_website": company.website_url or "",
                "contact_id": f"contact_{recipient_email.split('@')[0]}",
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
                "markdown_report": company.markdown_report
            }
            
            # Log the raw content being published
            print(f"📝 RAW CONTENT LOGGING: Publishing content to possibleminds.in")
            print(f"📝 Company: {company.company_name}")
            print(f"📝 Website: {company.website_url or 'N/A'}")
            print(f"📝 Recipient: {recipient_email}")
            print(f"📝 Content Length: {len(company.markdown_report) if company.markdown_report else 0} characters")
            print(f"📝 RAW MARKDOWN CONTENT START:")
            print(f"{'='*80}")
            print(f"{company.markdown_report}")
            print(f"{'='*80}")
            print(f"📝 RAW MARKDOWN CONTENT END")
            
            # Convert payload to JSON string (raw body for signature)
            raw_body = json.dumps(payload, separators=(',', ':'))
            
            # Also log the complete JSON payload being sent
            print(f"📝 COMPLETE JSON PAYLOAD START:")
            print(f"{'-'*80}")
            print(f"{json.dumps(payload, indent=2)}")
            print(f"{'-'*80}")
            print(f"📝 COMPLETE JSON PAYLOAD END")
            
            headers = {"Content-Type": "application/json"}
            
            # Calculate HMAC-SHA256 signature if secret is available
            if NETLIFY_SECRET:
                signature = hmac.new(
                    NETLIFY_SECRET.encode('utf-8'),
                    raw_body.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Hub-Signature-256"] = f"sha256={signature}"
                print(f"🔐 PROGRESS: Added webhook signature for secure publishing")
            else:
                print(f"⚠️ PROGRESS: No NETLIFY_WEBHOOK_SECRET found, publishing without signature")
            
            print(f"🌐 PROGRESS: Publishing report to possibleminds.in...")
            print(f"🔍 DEBUG: Publishing to: {NETLIFY_PUBLISH_URL}")
            
            # Make the request to publish (using raw JSON string)
            response = requests.post(
                NETLIFY_PUBLISH_URL,
                headers=headers,
                data=raw_body,  # Use raw JSON string for signature validation
                timeout=30
            )
            
            print(f"🔍 DEBUG: Netlify response status: {response.status_code}")
            
            # Log the complete response from possibleminds.in
            print(f"📝 POSSIBLEMINDS.IN RESPONSE START:")
            print(f"{'~'*80}")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            print(f"{'~'*80}")
            print(f"📝 POSSIBLEMINDS.IN RESPONSE END")
            
            if response.status_code == 200:
                result = response.json()
                # Extract publishUrl from the nested data structure
                public_url = result.get('data', {}).get('publishUrl') or result.get('public_url')
                
                print(f"🔍 DEBUG: Netlify response data: {result}")
                print(f"🔍 DEBUG: Extracted publishUrl: {public_url}")
                
                # Log the successful publishing details
                print(f"📝 PUBLISHING SUCCESS LOG:")
                print(f"📝 Company: {company.company_name}")
                print(f"📝 Published URL: {public_url}")
                print(f"📝 Tracking will be added to: {public_url}")
                
                if public_url:
                    print(f"✅ PROGRESS: Report published successfully to possibleminds.in")
                    print(f"🔗 PROGRESS: Adding tracking parameters to report URL")
                    
                    # Add tracking parameters to the public URL
                    tracking_params = {
                        'utm_source': 'email',
                        'utm_medium': 'outreach',
                        'utm_campaign': 'deep_research',
                        'utm_content': 'strategic_analysis',
                        'company': company.company_name.lower().replace(' ', '_'),
                        'recipient': recipient_email.split('@')[0] if recipient_email else 'unknown'
                    }
                    
                    url_params = urllib.parse.urlencode(tracking_params)
                    tracked_url = f"{public_url}?{url_params}"
                    
                    print(f"✅ PROGRESS: Tracking-enabled report URL ready")
                    print(f"🔍 DEBUG: Final tracked URL: {tracked_url}")
                    return tracked_url
                else:
                    print(f"❌ PROGRESS: Failed to extract public URL from response")
                    print(f"🔍 DEBUG: Response data: {result}")
                    return ""
            else:
                print(f"❌ PROGRESS: Report publishing failed (HTTP {response.status_code})")
                print(f"🔍 DEBUG: Response: {response.text}")
                return ""
                
        except Exception as e:
            print(f"❌ PROGRESS: Report publishing error: {e}")
            return ""

    def _get_company_research_with_full_report(self, company_name: str, auto_trigger: bool = True) -> tuple[str, int]:
        """Get company research data and ensure full report is available. Returns (research_text, company_id)."""
        if not company_name:
            print(f"🔍 DEBUG: No company name provided")
            return "", None
            
        print(f"🔍 DEBUG: Looking up company: {company_name}")
        
        try:
            # Import here to avoid circular imports
            from app.models.company import Company
            
            # Try to find company by name
            companies = Company.get_companies_by_name(company_name)
            print(f"🔍 DEBUG: Found {len(companies)} companies matching '{company_name}'")
            
            # If company not found and auto-trigger enabled, create company and start research
            if not companies and auto_trigger:
                print(f"🔍 Starting auto-research for {company_name}...")
                return self._trigger_full_deep_research(company_name)
            elif not companies:
                print(f"🔍 DEBUG: No companies found and auto-trigger disabled")
                return "", None
            
            company = companies[0]  # Take first match
            print(f"🔍 DEBUG: Using company ID: {company.id}")
            print(f"🔍 DEBUG: Company has markdown_report: {hasattr(company, 'markdown_report') and bool(company.markdown_report)}")
            print(f"🔍 DEBUG: Company research_status: {getattr(company, 'research_status', 'unknown')}")
            
            # Check if we have a published markdown report (full research completed)
            if hasattr(company, 'markdown_report') and company.markdown_report:
                print(f"📊 Using full research report for {company_name}")
                # Use basic research for email context, but we have the full report published
                research_text = company.research_step_1_basic or company.company_research or company.markdown_report[:500] + "..."
                return research_text, company.id
            
            # Check if we have basic research but need full report
            elif hasattr(company, 'research_step_1_basic') and company.research_step_1_basic:
                print(f"🔍 DEBUG: Company has basic research: {len(company.research_step_1_basic)} chars")
                if auto_trigger:
                    print(f"🔍 Upgrading to full research for {company_name}...")
                    return self._trigger_full_deep_research(company_name, company.id)
                else:
                    print(f"📊 Using basic research for {company_name}")
                    return company.research_step_1_basic, company.id
            
            # Check if we have old-style company research but need full report
            elif hasattr(company, 'company_research') and company.company_research:
                print(f"🔍 DEBUG: Company has old-style research: {len(company.company_research)} chars")
                if auto_trigger:
                    print(f"🔍 Upgrading to full research for {company_name}...")
                    return self._trigger_full_deep_research(company_name, company.id)
                else:
                    print(f"📊 Using existing research for {company_name}")
                    return company.company_research, company.id
            
            else:
                # Company exists but no research data - trigger if auto_trigger enabled
                print(f"🔍 DEBUG: Company exists but no research data found")
                if auto_trigger:
                    print(f"🔍 Starting research for {company_name}...")
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
            
            print(f"🚀 Researching {company_name}...")
            
            # If no company_id provided, we need to create the company first
            if company_id is None:
                # Create basic company record
                company_data = {
                    'company_name': company_name,
                    'website_url': '',  # Will be filled if domain info available
                    'company_research': ''
                }
                
                if Company.save(company_data):
                    # Get the newly created company
                    companies = Company.get_companies_by_name(company_name)
                    if companies:
                        company_id = companies[0].id
                        print(f"✅ Created company record for {company_name}")
                    else:
                        print(f"❌ Failed to retrieve created company: {company_name}")
                        return ""
                else:
                    print(f"❌ Failed to create company record for: {company_name}")
                    return ""
            
            # Perform basic research using AI service
            ai_service = AIResearchService()
            research_result = ai_service.research_company(company_name, "")
            
            if research_result:
                # Update company with research data
                Company.update_research_step(company_id, 1, research_result)
                Company.update_research_status(company_id, 'completed')
                
                print(f"✅ Research completed for {company_name}")
                return research_result
            else:
                print(f"❌ Research failed for {company_name}")
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
            
            print(f"🚀 Starting deep research for {company_name}...")
            
            # If no company_id provided, we need to create the company first
            if company_id is None:
                # Create basic company record
                company_data = {
                    'company_name': company_name,
                    'website_url': '',  # Will be filled if domain info available
                    'company_research': ''
                }
                
                if Company.save(company_data):
                    # Get the newly created company
                    companies = Company.get_companies_by_name(company_name)
                    if companies:
                        company_id = companies[0].id
                        print(f"✅ Created company record for {company_name}")
                    else:
                        return "", None
                else:
                    return "", None
            
            # Trigger step-by-step deep research
            researcher = StepByStepResearcher()
            result = researcher.start_deep_research(company_id, force_refresh=False)
            
            if result.get('success'):
                print(f"⏳ Waiting for research completion...")
                
                # Wait for research to complete with polling (max 60 seconds)
                max_wait_time = 60
                poll_interval = 3
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    
                    # Check if research is completed
                    company = Company.get_by_id(company_id)
                    if company and company.research_status == 'completed' and company.markdown_report:
                        print(f"✅ Full research completed for {company_name}")
                        # Use basic research for email context
                        research_text = company.research_step_1_basic or company.company_research or "Research completed - see full report for details."
                        return research_text, company_id
                    elif company and company.research_step_1_basic:
                        print(f"📊 Basic research available for {company_name}")
                        return company.research_step_1_basic, company_id
                    elif company and company.research_status == 'failed':
                        print(f"❌ Research failed for {company_name}")
                        break
                
                # Timeout or failure - try to get whatever research is available
                company = Company.get_by_id(company_id)
                if company and (company.research_step_1_basic or company.company_research):
                    research_text = company.research_step_1_basic or company.company_research
                    print(f"⚠️ Using partial research for {company_name}")
                    return research_text, company_id
                else:
                    print(f"❌ No research data available for {company_name}")
                    return "", company_id
            else:
                print(f"❌ Failed to start research for {company_name}")
                return "", company_id
                
        except Exception as e:
            print(f"❌ Research error for {company_name}: {e}")
            return "", company_id

    def _generate_report_url_with_tracking(self, company_id: int, company_name: str, recipient_email: str, campaign_id: int = None) -> str:
        """Generate a public report URL with tracking parameters for possibleminds.in."""
        import time
        import uuid
        
        print(f"🔍 DEBUG: Generating report URL for company_id: {company_id}")
        
        if not company_id:
            print(f"🔍 DEBUG: No company_id provided, returning empty URL")
            return ""
        
        try:
            # Base click tracking URL for possibleminds.in
            base_url = "https://possibleminds.in/.netlify/functions/click-tracking"
            print(f"🔍 DEBUG: Base URL: {base_url}")
            
            # Generate company slug from company name
            company_slug = company_name.lower().replace(' ', '-').replace('&', 'and') if company_name else f"company-{company_id}"
            
            # Tracking parameters matching possibleminds.in format
            tracking_params = {
                'company_id': company_slug,
                'utm_source': 'email',
                'utm_medium': 'outreach',
                'utm_campaign': f"campaign_{campaign_id}" if campaign_id else 'deep_research',
                'utm_content': 'strategic_analysis',
                'company': company_name if company_name else 'unknown',
                'recipient': recipient_email.split('@')[0] if recipient_email else 'unknown',
                'campaign_id': campaign_id if campaign_id else 'unknown',
                'tracking_id': f"tr_{uuid.uuid4().hex[:8]}",
                'timestamp': int(time.time())
            }
            
            # Build URL with tracking parameters
            url_params = urllib.parse.urlencode(tracking_params)
            tracked_url = f"{base_url}?{url_params}"
            
            print(f"🔍 DEBUG: Final tracked URL: {tracked_url}")
            return tracked_url
            
        except Exception as e:
            print(f"❌ Error generating report URL: {e}")
            # Return basic URL without tracking as fallback
            fallback_url = f"https://possibleminds.in/.netlify/functions/click-tracking?company_id={company_id}&utm_source=email"
            print(f"🔍 DEBUG: Using fallback URL: {fallback_url}")
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
    def _signature() -> str:
        """Generate email signature."""
        return """Pranav Modi
Founder, Possible Minds
📧 pranav@possibleminds.in
🌐 possibleminds.in""" 