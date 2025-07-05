# email_composer_deep_research.py  ── v1 (research-backed, personalized outreach)

import os, random, textwrap, json, pathlib
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
            12. Add a blank line, then include: "P.S. Happy to share how we helped Precise Imaging reduce appointment no-shows by 40% - similar healthcare operational challenges."

            IMPORTANT: 
            - If company research is provided, MUST use specific insights from it
            - If no research available, focus on general industry pain points but still be specific
            - Keep total words ≤ 180
            - Subject MUST start with "Subject:" as the first line
            - Use specific, actionable language
            - Reference real business metrics when possible

            Here is context about the sender and their product:
            """ + SENDER_INFO)

    def compose_email(self, lead: Dict[str, str], calendar_url: str = DEFAULT_CALENDAR, extra_context: str | None = None, auto_research: bool = None) -> Dict[str, str] | None:
        if not self.product_desc:
            print("❗ productdescription.txt missing – aborting.")
            return None

        first_name = lead.get("name", "").split()[0] if lead.get("name") else "there"
        company_name = lead.get("company", "")
        proof = random.choice(self.proof_points) if self.proof_points else ""

        # Use global setting if auto_research not specified
        if auto_research is None:
            auto_research = AUTO_RESEARCH

        # Try to get company research data (with optional auto-triggering)
        company_research = self._get_company_research(company_name, auto_trigger=auto_research)

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
        print("User prompt:", user_prompt)  # Debug log

        try:
            print("Sending request to OpenAI...")  # Debug log
            rsp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.7,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            print("Raw OpenAI response:", rsp)  # Debug log
            print("Response content:", rsp.choices[0].message.content)  # Debug log
        except Exception as e:
            print("🔴 OpenAI error:", e)
            return None

        subject, body = self._parse(rsp.choices[0].message.content)
        print("Parsed subject:", subject)  # Debug log
        print("Parsed body (before signature):", body)  # Debug log
        
        body = body.strip() # Ensure no trailing newlines before adding signature
        body += '\n\n' + self._signature()
        
        result = {"subject": subject, "body": body}
        print("Final result (with signature):", result)  # Debug log
        return result

    def _get_company_research(self, company_name: str, auto_trigger: bool = True) -> str:
        """Get company research data from the database if available. Optionally trigger research if missing."""
        if not company_name:
            return ""
            
        try:
            # Import here to avoid circular imports
            from app.models.company import Company
            
            # Try to find company by name
            companies = Company.get_companies_by_name(company_name)
            
            # If company not found and auto-trigger enabled, create company and start research
            if not companies and auto_trigger:
                print(f"🔍 Company '{company_name}' not found. Auto-triggering research...")
                return self._trigger_company_research(company_name)
            elif not companies:
                print(f"No research found for company: {company_name}")
                return ""
            
            company = companies[0]  # Take first match
            
            # Check if we have research data
            if hasattr(company, 'company_research') and company.company_research:
                print(f"Found research for {company_name}: {len(company.company_research)} characters")
                return company.company_research
            elif hasattr(company, 'research_step_1_basic') and company.research_step_1_basic:
                print(f"Found basic research for {company_name}: {len(company.research_step_1_basic)} characters")
                return company.research_step_1_basic
            else:
                # Company exists but no research data - trigger if auto_trigger enabled
                if auto_trigger:
                    print(f"🔍 Company '{company_name}' exists but has no research. Auto-triggering research...")
                    return self._trigger_company_research(company_name, company.id)
                else:
                    print(f"No research data available for company: {company_name}")
                    return ""
                
        except Exception as e:
            print(f"Error fetching company research for {company_name}: {e}")
            return ""

    def _trigger_company_research(self, company_name: str, company_id: int = None) -> str:
        """Trigger deep research for a company and return basic research if successful."""
        try:
            # Import research services
            from deepresearch.ai_research_service import AIResearchService
            from app.models.company import Company
            
            print(f"🚀 Starting automatic research for: {company_name}")
            
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
                        print(f"✅ Created company record for {company_name} with ID: {company_id}")
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
                
                print(f"✅ Auto-research completed for {company_name}: {len(research_result)} characters")
                return research_result
            else:
                print(f"❌ Auto-research failed for: {company_name}")
                return ""
                
        except Exception as e:
            print(f"❌ Error during auto-research for {company_name}: {e}")
            return ""

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
        print("Split lines:", lines)  # Debug log
        
        # Find subject line
        body_start_index = 0
        for i, line in enumerate(lines):
            print(f"Processing line {i}: {line}")  # Debug log
            if line.lower().startswith("subject:"):
                subj = line.split(":", 1)[1].strip()
                print(f"Found subject: {subj}")  # Debug log
                body_start_index = i + 1
                break
        
        # If no subject line found, use default format
        if not subj:
            subj = "[Company] → AI Transformation?"
            print(f"No subject found, using default: {subj}")
            body_start_index = 0  # Use all lines for body when no subject found

        # Get all lines after subject as body, preserving empty lines for paragraph spacing
        body_lines = []
        if body_start_index < len(lines):
            stop_phrases = ("warm regards,", "best regards,", "sincerely,", "cheers,", "regards,", "best,", "thanks,", "yours,", "kind regards,")
            
            for line_content in lines[body_start_index:]:
                line_lower = line_content.lower().strip()
                
                # Only check for stop phrases as standalone sign-offs (not within paragraphs)
                if any(line_lower == phrase for phrase in stop_phrases):
                    break
                
                body_lines.append(line_content)
            
            body = '\n'.join(body_lines).strip()
            print(f"Parsed body: {body}")
        
        return subj, body

    @staticmethod
    def _signature() -> str:
        """Generate email signature."""
        return """Pranav Modi
Founder, Possible Minds
📧 pranav@possibleminds.in
🌐 possibleminds.in""" 