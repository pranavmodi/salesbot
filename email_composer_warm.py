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
            
            It should feel like a human note, not a sales pitch. Avoid hard selling, bullets, or heavy formatting.
            Think like a thoughtful investor or potential collaborator reaching out to a founder they respect.

            Use this format:
            
            Subject: A sincere, brief phrase (no marketing speak)
            
            Body:
            1. Greeting using the person's first name
            2. A short and natural intro about who you are (1 sentence)
            3. Say what you found interesting about their work or company (use context if provided)
            4. Offer a light, low-pressure invitation to talk — leave room for them to say no
            5. Friendly sign-off
            
            Stay under 120 words. Casual and kind tone. Let them feel safe and in control.

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
        print("Parsed body:", body)  # Debug log
        
        result = {"subject": subject, "body": body.strip()}
        print("Final result:", result)  # Debug log
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
        for i, line in enumerate(lines):
            print(f"Processing line {i}: {line}")  # Debug log
            if line.lower().startswith("subject:"):
                subj = line.split(":", 1)[1].strip()
                print(f"Found subject: {subj}")  # Debug log
                # Get all lines after subject as body
                body_lines = []
                for body_line in lines[i+1:]:
                    if body_line.lower().startswith("warm regards,"):
                        break
                    body_lines.append(body_line)
                body = "\n".join(body_lines).strip()
                break
        
        print(f"Parsed subject: {subj}")  # Debug log
        print(f"Parsed body: {body}")  # Debug log
        
        return subj, body

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