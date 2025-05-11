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
        self.client         = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.product_desc   = self._load_text(PRODUCT_DESC_PATH)
        self.proof_points   = self._load_text(PROOF_POINTS_PATH).splitlines()

        self.system_prompt = textwrap.dedent("""
            You're writing a warm, curious email to a founder you genuinely want to connect with.
            
            It should feel like a human note, not a sales pitch. Use simple language, no business-speak. Avoid hard selling, bullets, or heavy formatting.
            Think like a thoughtful investor or potential collaborator reaching out to a founder they respect.

            Use this format:
            
            Subject: use this text "Our work at Possible Minds" ( do not use name in subject)
            
            Body:
            1. Greeting using only the person's first name followed by a comma and newline (no "Hi" or "Hello")
            2. "I'm curious to hear about the current problems your team is solving or the new things you're building at (shortened if needed)<company name>"
            3. A short and natural intro about you (I'm the founder of Possible minds) and your interest in creating AI agents for healthcare (1-2 short sentences)
            4. Briefly mention the product and how it's deployed at healthcare companies like Precise Imaging (1 sentence)
            5. Offer a light, low-pressure invitation to talk — leave room for them to say no
            7. End with "I know you're busy in your journey so if you are not interested please let me know and I'll stop emailing :)"
            8. Friendly sign-off (e.g. "Best," - DO NOT include name here, it will be added later)

            IMPORTANT: You MUST include "Subject: Our work at Possible Minds" as the first line of your response.
            DO NOT start with the person's name as the first line of your response.
            
            Stay under 120 words. Casual and kind tone. Let them feel safe and in control. Do not use overused, business-speak words like synergy.

            Here is some context about the sender and their product:
            """ + SENDER_INFO)

    def compose_email(self, lead: Dict[str, str], calendar_url: str = DEFAULT_CALENDAR, extra_context: str | None = None) -> Dict[str, str] | None:
        if not self.product_desc:
            print("❗ productdescription.txt missing – aborting.")
            return None

        first_name = lead.get("name", "").split()[0] if lead.get("name") else "there"
        proof = random.choice(self.proof_points) if self.proof_points else ""

        user_prompt = f"""
        === Lead ===
        {self._fmt_dict(lead)}

        === First name ===
        {first_name}

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
        print("Parsed body (before signature):", body)  # Debug log
        
        body = body.strip() # Ensure no trailing newlines before adding signature
        body += '\n\n' + self._signature()
        
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
        lines = [l for l in raw.strip().splitlines() if l]
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
        
        # If no subject line found, use default
        if not subj:
            subj = "Our work at Possible Minds"
            print(f"No subject found, using default: {subj}")
            body_start_index = 0  # Use all lines for body when no subject found

        # Get all lines after subject as body, stopping before common sign-offs
        body_lines = []
        if body_start_index < len(lines):
            stop_phrases = ("warm regards,", "best regards,", "sincerely,", "cheers,", "regards,", "best,", "thanks,", "yours,", "kind regards,")
            for line_content in lines[body_start_index:]:
                found_stop = False
                for phrase in stop_phrases:
                    # Check if the line *starts with* a stop phrase (case-insensitive, ignoring leading/trailing whitespace on the line)
                    if line_content.lower().strip().startswith(phrase):
                        found_stop = True
                        break
                if found_stop:
                    break 
                body_lines.append(line_content)
        
        body = "\n".join(body_lines).strip()
        
        # If body is empty and subject wasn't prefixed, assume entire raw content (minus first line) was body
        if not body and not raw.lower().strip().startswith("subject:"):
            # We're now handling this case with the default subject, so just use all lines
            body = "\n".join(lines).strip()
            # Re-apply stop phrase stripping
            temp_body_lines = body.splitlines()
            final_body_lines = []
            for line_content in temp_body_lines:
                found_stop = False
                for phrase in stop_phrases:
                    if line_content.lower().strip().startswith(phrase):
                        found_stop = True
                        break
                if found_stop:
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
        "name": "Kristin Graves",
        "company": "Fast Pace Health",
        "position": "VP of Talent",
        "email": "kristin.graves@fastpacehealth.com",
    }
    email = composer.compose_email(lead_example)
    if email:
        print("=" * 72)
        print("SUBJECT:", email["subject"])
        print("-" * 72)
        print(email["body"]) 