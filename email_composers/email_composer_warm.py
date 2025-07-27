# email_composer_warm.py  ── v3 (less sales-ey, more personal, Lily-style)

import os, random, textwrap, json, pathlib
from typing import Dict, Tuple, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

import pathlib
_current_dir = pathlib.Path(__file__).parent
PRODUCT_DESC_PATH = str(_current_dir / "productdescription.txt")
PROOF_POINTS_PATH = str(_current_dir / "proofpoints.txt")
KPI_HINTS_PATH    = os.getenv("KPI_HINTS_PATH", "")
DEFAULT_CALENDAR  = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o")

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

class WarmEmailComposer:
    """
    Compose more personal, founder-friendly emails inspired by Lily from Flex Capital.
    """

    def __init__(self) -> None:
        self.client         = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.product_desc   = self._load_text(PRODUCT_DESC_PATH)
        self.proof_points   = self._load_text(PROOF_POINTS_PATH).splitlines()

        self.system_prompt = textwrap.dedent("""
            You're writing a warm, curious email to a founder you genuinely want to connect with.
            
            It should feel like a human note, not a sales pitch. Use simple language, no business-speak. Avoid hard selling or heavy formatting.
            Think like a thoughtful investor or potential collaborator reaching out to a founder they respect.

            Use this format:
            
            Subject: use this text "Possible Minds <> [company name]" (replace [company name] with the actual company name)
            
            Body:
            1. Greeting - first name only followed by a comma on its own line
            2. Add a blank line after the greeting
            3. First paragraph (EXACTLY ONE SENTENCE): Express genuine curiosity about how they're using AI to create impact at their company. Use phrasing like "I'm curious about how you're using AI to create impact at [shortened company name]". Keep it brief and focused - do not add additional sentences about enhancing specific aspects of their business.
            4. Add a blank line between paragraphs
            5. Second paragraph (2-3 sentences): Brief intro starting with "I'm the founder of Possible Minds", mention your focus on AI Agents for healthcare
            6. Add a blank line
            7. Third paragraph (1-2 sentences): Briefly mention your AI chatbot is helping "healthcare companies like yours" - do NOT mention Precise Imaging here
            8. Add a blank line
            9. Fourth paragraph: A direct, crisp invitation to chat - something like "I'd love to connect and explore collaboration between our teams." Avoid phrases like "no pressure" or other filler words.
            10. Add a blank line
            11. Final line: "I know you're busy in your journey so if you are not interested please let me know and I'll stop emailing :)"
            12. Sign-off on its own line (e.g., "Best," - DO NOT include name here, it will be added later)
            13. ALWAYS add two blank lines after the sign-off, then include: "p.s. in good company - we've successfully deployed at Precise Imaging where our chatbot is helping reduce appointment no-shows and improving patient engagement."

            IMPORTANT: The p.s. section MUST be included. This is REQUIRED in EVERY email.
            IMPORTANT: You MUST include "Subject: Our work at Possible Minds" as the first line of your response.
            DO NOT start with the person's name as the first line of your response.
            
            Stay under 150 words. Casual and kind tone. Let them feel safe and in control. Use blank lines between paragraphs.

            Here is some context about the sender and their product:
            """ + SENDER_INFO)

    def compose_email(self, lead: Dict[str, str], calendar_url: str = DEFAULT_CALENDAR, extra_context: str | None = None) -> Dict[str, str] | None:
        if not self.product_desc:
            print("❗ productdescription.txt missing – aborting.")
            return None

        first_name = lead.get("name", "").split()[0] if lead.get("name") else "there"
        company_name = lead.get("company", "")
        proof = random.choice(self.proof_points) if self.proof_points else ""

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

        {extra_context or ''}
        """
        print("User prompt:", user_prompt)  # Debug log

        try:
            print("Sending request to OpenAI...")  # Debug log
            rsp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.7,
                max_tokens=400,
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
        
        # Ensure company name is in the subject
        if "[company]" in subject or "[company name]" in subject:
            subject = subject.replace("[company]", company_name).replace("[company name]", company_name)
        elif company_name and "<>" in subject and company_name not in subject:
            # If format is already correct but missing company name
            subject = f"Possible Minds <> {company_name}"
        
        print("Final subject:", subject)  # Debug log
        print("Parsed body (before signature):", body)  # Debug log
        
        body = body.strip() # Ensure no trailing newlines before adding signature
        body += '\n\n' + self._signature()
        
        # Check if p.s. section is missing and add it if needed
        ps_text = "p.s. in good company - we've successfully deployed at Precise Imaging where our chatbot is helping reduce appointment no-shows and improving patient engagement."
        if not "p.s." in body.lower():
            body += f"\n\n{ps_text}"
            print("Added missing p.s. section")
        
        result = {"subject": subject, "body": body}
        print("Final result (with signature):", result)  # Debug log
        return result

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
        
        # If no subject line found, use default - this will be updated with actual company name in compose_email
        if not subj:
            subj = "Possible Minds <> [company]"
            print(f"No subject found, using default: {subj}")
            body_start_index = 0  # Use all lines for body when no subject found

        # Get all lines after subject as body, preserving empty lines for paragraph spacing
        body_lines = []
        if body_start_index < len(lines):
            stop_phrases = ("warm regards,", "best regards,", "sincerely,", "cheers,", "regards,", "best,", "thanks,", "yours,", "kind regards,")
            in_ps_section = False
            
            for line_content in lines[body_start_index:]:
                line_lower = line_content.lower().strip()
                
                # Skip processing if we've reached a p.s. section or we're already in one
                if line_lower.startswith("p.s.") or in_ps_section:
                    in_ps_section = True
                    body_lines.append(line_content)
                    continue
                
                # Only check for stop phrases as standalone sign-offs (not within paragraphs)
                if any(line_lower == phrase for phrase in stop_phrases):
                    break
                    
                body_lines.append(line_content)
        
        # Join with newlines to preserve paragraph structure
        body = "\n".join(body_lines).strip()
        
        # Add a fallback if body is completely empty
        if not body:
            # Use all content but with stop phrases removed
            body = "\n".join(lines).strip()
            temp_body_lines = body.splitlines()
            final_body_lines = []
            in_ps_section = False
            
            for line_content in temp_body_lines:
                line_lower = line_content.lower().strip()
                
                # Skip processing if we've reached a p.s. section or we're already in one
                if line_lower.startswith("p.s.") or in_ps_section:
                    in_ps_section = True
                    final_body_lines.append(line_content)
                    continue
                    
                if any(line_lower == phrase for phrase in stop_phrases):
                    break
                    
                final_body_lines.append(line_content)
                
            body = "\n".join(final_body_lines).strip()

        print(f"Parsed subject: {subj}")  # Debug log
        print(f"Parsed body (after stripping stop phrases): {body}")  # Debug log
        
        return subj, body

    @staticmethod
    def _signature() -> str:
        return """Cheers,

Pranav Modi
CEO · Possible Minds (https://possibleminds.in)
https://www.linkedin.com/in/pranav-modi-5a3a9b7/"""

# Example usage:
if __name__ == "__main__":
    composer = WarmEmailComposer()
    lead_example = {
        "name": "Andy Smith",
        "company": "GoHealth Urgent Care",
        "position": "Chief Technology Officer",
        "email": "andy.smith@gohealthuc.com",
    }
    email = composer.compose_email(lead_example)
    if email:
        print("=" * 72)
        print("SUBJECT:", email["subject"])
        print("-" * 72)
        print(email["body"]) 