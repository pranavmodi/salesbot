# email_composer_warm.py  ── v3 (less sales-ey, more personal, Lily-style)

import os, random, textwrap, json, pathlib, yaml
from typing import Dict, Tuple, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PRODUCT_DESC_PATH = "productdescription.txt"
PROOF_POINTS_PATH = "proofpoints.txt"
KPI_HINTS_PATH    = os.getenv("KPI_HINTS_PATH", "")
DEFAULT_CALENDAR  = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o")
SENDER_NAME       = "Pranav Modi"

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

class AltSubjectEmailComposer:
    """
    Email composer that uses the subject line: "Are you AI pilled yet at <company name> ? "
    """

    def __init__(self) -> None:
        self.client         = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.product_desc   = self._load_text(PRODUCT_DESC_PATH)
        self.proof_points   = self._load_text(PROOF_POINTS_PATH).splitlines()
        self.kpi_hints      = self._load_kpi_hints()
        self.system_prompt = (f"""
You are a helpful assistant who writes short, friendly founder-style
outreach emails to B2B leads. Your single goal: book a 15-minute call
(via the Calendly link you'll see below).

===== FORMAT =====
Subject: <one line>
<blank line>
<body>

===== SUBJECT RULES =====
• MUST contain both <first-name> and <company-name>.  
  (e.g.  "Andy, AI momentum at GoHealth?")  
• Keep it to ≤ 7 words.  
• No emojis.

===== BODY RULES =====
• MUST open exactly:  
  Hi <first-name>, I'm curious to know how you are leveraging AI at <company-name>.
• MUST follow with this intro line:  
  I'm Pranav, founder of Possible Minds — we help businesses boost support efficiency and customer experience with a 24/7 AI chatbot trained on their own content.
• 2–3 micro-paragraphs, ≤ 150 words total.
• Include the following THREE talking points (wording may vary):  
  1. Business leaders warn that firms ignoring AI will be left behind.  
  2. Others in <industry> are already leveraging AI.  
  3. Possible Minds is trusted by Precise Imaging and others.
• **Embed exactly ONE of these quotes where it has most impact**  
  (use it verbatim, wrapped in quotation marks):  
  — "AI is more profound than fire or electricity." — Sundar Pichai  
  — "We're at the start of a new era of computing." — Satya Nadella  
  — "Companies that don't deploy it will get left behind." — Trey Lowe
• Mention our deployment at  
  Precise Imaging (https://precisemri.com).
• Finish with this exact closing paragraph, verbatim:  
  — We're at the start of a new era of computing, and we're in active conversations with other healthcare and service companies exploring similar use cases. Got 15 minutes next week to see what AI could do for you? Lock in a slot here: {DEFAULT_CALENDAR}

===== STYLE =====
Friendly, human, mildly informal (Lily-from-Flex vibe).  
No buzzwords, no signature – the script adds it.
""" + SENDER_INFO)

    def compose_email(self, lead: Dict[str, str], calendar_url: str = DEFAULT_CALENDAR, extra_context: str | None = None) -> Dict[str, str] | None:
        if not self.product_desc:
            print("❗ productdescription.txt missing – aborting.")
            return None

        # Extract lead information for the prompt
        prompt_first_name = lead.get("name", "").split()[0] if lead.get("name") else "there"
        prompt_company_name = lead.get("company", "")
        proof = random.choice(self.proof_points) if self.proof_points else ""

        user_prompt = f"""
        === Lead ===
        {self._fmt_dict(lead)}

        === First name ===
        {prompt_first_name}

        === Company name ===
        {prompt_company_name}

        === Product description ===
        {self.product_desc}

        === Proof point (optional) ===
        {proof}

        === Required opening ===
        The email body MUST start with: "Hi {prompt_first_name}, I'm curious to know how you are leveraging AI at {prompt_company_name}."

        === Required intro line ===
        The email body MUST follow the opening with: "I'm Pranav, founder of Possible Minds — we help businesses boost support efficiency and customer experience with a 24/7 AI chatbot trained on their own content."

        === Required examples ===
        The email MUST mention how we're helping other companies, specifically:
        - Mention "Precise Imaging (https://precisemri.com)" as a plain URL
        - Reference "other healthcare and service companies" we're working with

        {extra_context or ''}
        """
        # print("User prompt:", user_prompt)  # Debug log

        try:
            # print("Sending request to OpenAI...")  # Debug log
            rsp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.7,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            # print("Raw OpenAI response:", rsp)  # Debug log
            # print("Response content:", rsp.choices[0].message.content)  # Debug log
        except Exception as e:
            print("🔴 OpenAI error:", e)
            return None

        # Parse the AI-generated subject and body
        ai_subject, body = self._parse(rsp.choices[0].message.content)
        # print("Parsed AI subject:", ai_subject) # Debug log
        
        # --- START: New Subject Line Logic ---
        # Use the first name and company name for the new subject line format
        first = prompt_first_name        # already computed above
        company = prompt_company_name or "your company"
        subject = f"{first}, AI momentum at {company}?"
        # --- END: New Subject Line Logic ---

        # print("Final subject:", subject)  # Debug log
        # print("Parsed body (before signature):", body)  # Debug log
        
        body = body.strip() # Ensure no trailing newlines before adding signature
        body += '\n\n' + self._signature()
        
        # Convert to plain text format (strip any HTML tags)
        plain_text_body = self._convert_to_plain_text(body)
        
        result = {"subject": subject, "body": plain_text_body, "format": "text"}
        # print("Final result (with signature):", result)  # Debug log
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
        # print("Split lines:", lines)  # Debug log
        
        # Find subject line
        body_start_index = 0
        for i, line in enumerate(lines):
            # print(f"Processing line {i}: {line}")  # Debug log
            if line.lower().startswith("subject:"):
                subj = line.split(":", 1)[1].strip()
                # print(f"Found subject: {subj}")  # Debug log
                body_start_index = i + 1
                break
        
        if not subj:
            # If AI doesn't provide a subject, we won't use it anyway with the new logic,
            # but we still need to parse the body correctly.
            # print(f"No subject found by AI, body will start from line 0")
            body_start_index = 0

        body_lines = []
        if body_start_index < len(lines):
            body_lines = lines[body_start_index:]
        
        # Strip any signature-like phrases from the end of the body
        stop_phrases = [
            "cheers,", "best,", "regards,", "sincerely,", 
            "thanks,", "thank you,", SENDER_NAME.lower()
        ]
        
        while body_lines:
            last_line_stripped = body_lines[-1].strip().lower()
            if any(phrase in last_line_stripped for phrase in stop_phrases):
                body_lines.pop()
            elif not last_line_stripped: # remove empty trailing lines
                body_lines.pop()
            else:
                break
        
        body = "\n".join(body_lines).strip()
        
        # print(f"Parsed AI subject: {subj}")  # Debug log
        # print(f"Parsed body (after stripping stop phrases): {body}")  # Debug log
        
        return subj, body # Return the AI's subject too, though we override it

    @staticmethod
    def _signature() -> str:
        return """Cheers,

Pranav Modi
CEO · Possible Minds (https://possibleminds.in)
https://www.linkedin.com/in/pranav-modi-5a3a9b7/"""

    @staticmethod
    def _load_kpi_hints() -> Dict[str, str]:
        # (This method would be the same as in WarmEmailComposer)
        # For brevity, assuming it exists and loads KPI hints correctly
        # Example structure:
        return {
            "VP OF TALENT": "Focus on reducing hiring time and improving candidate experience.",
            "CHIEF TECHNOLOGY OFFICER": "Highlight scalability and integration capabilities."
        } 

    def _convert_to_plain_text(self, text: str) -> str:
        """Convert email body to plain text format, stripping all HTML tags."""
        import re
        
        # Convert anchor tags to plain URLs
        # Pattern: <a href="URL">text</a> -> text (URL)
        def replace_anchor(match):
            url = match.group(1)
            link_text = match.group(2)
            # If the link text is the same as URL (like precisemri.com), just return the URL
            if link_text.strip() == url.replace('https://', '').replace('http://', ''):
                return url
            else:
                return f"{link_text} ({url})"
        
        # Replace anchor tags with plain text
        text = re.sub(r'<a href="([^"]*)"[^>]*>([^<]*)</a>', replace_anchor, text)
        
        # Strip any remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up any HTML entities that might remain
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        
        return text

# Example usage (for testing this file directly)
if __name__ == "__main__":
    composer = AltSubjectEmailComposer()
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