# email_composer.py
import os, random, textwrap, json, pathlib, yaml
from typing import Dict, Tuple, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PRODUCT_DESC_PATH   = "productdescription.txt"        # required
PROOF_POINTS_PATH   = "proofpoints.txt"               # optional
KPI_HINTS_PATH      = os.getenv("KPI_HINTS_PATH", "") # optional YAML / JSON
DEFAULT_CALENDAR    = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
OPENAI_MODEL        = os.getenv("OPENAI_MODEL", "gpt-4o")

class EmailComposer:
    """Compose cold emails; KPI context comes from file OR is inferred by the LLM."""

    # --------------------------------------------------------------------- #
    def __init__(self) -> None:
        self.client              = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.product_desc        = self._load_text(PRODUCT_DESC_PATH)
        self.proof_points        = self._load_text(PROOF_POINTS_PATH).splitlines()
        self.kpi_hints           = self._load_kpi_hints(KPI_HINTS_PATH)

        self.system_prompt = textwrap.dedent("""
            You are an elite SDR who writes outcome-driven cold emails.

            • Subject = KPI question or promise (≤7 words)  
            • 1-sentence opener = social proof metric from a similar company (use provided proof point)  
            • Max 4 short paragraphs (≤2 lines each)  
            • Tie value to 2-3 KPIs for the lead’s title.  
              - If explicit KPI hints are supplied, **use them**.  
              - Otherwise, infer realistic KPIs for that title in a US healthcare context.  
            • Finish with the provided CTA *verbatim*, no extras.  
            • NO signature or closing – the script appends those.  

            Output schema **exactly**:

            Subject: <subject line>
            Body:
            <body text with line breaks>
        """)

    # --------------------------------------------------------------------- #
    def compose_email(
        self,
        lead: Dict[str, str],
        calendar_url: str = DEFAULT_CALENDAR,
        extra_context: str | None = None
    ) -> Dict[str, str] | None:

        if not self.product_desc:
            print("❗ productdescription.txt missing – aborting.")
            return None

        title      = lead.get("position", "").strip()
        kpi_prompt = self.kpi_hints.get(title.upper(), "")
        proof      = random.choice(self.proof_points) if self.proof_points else ""
        cta        = (
            f"➡️ *Worth 15 min?* Pick a slot 👉 {calendar_url}\n"
            "Or reply **1** for yes / **2** for later."
        )

        user_prompt = f"""
        === Lead ===
        {self._fmt_dict(lead)}

        === Product description ===
        {self.product_desc}

        === Proof point ===
        {proof}

        === KPI hints (may be empty) ===
        {kpi_prompt}

        === CTA (use verbatim at end) ===
        {cta}

        {extra_context or ''}
        """

        try:
            rsp = self.client.chat.completions.create(
                model      = OPENAI_MODEL,
                temperature= 0.6,
                max_tokens = 400,
                messages   = [
                    {"role":"system","content":self.system_prompt},
                    {"role":"user","content": user_prompt}
                ]
            )
        except Exception as e:
            print("🔴 OpenAI error:", e)
            return None

        subj, body = self._parse(rsp.choices[0].message.content)
        body += self._signature()
        return {"subject": subj, "body": body}

    # ------------------------------- helpers ----------------------------- #
    @staticmethod
    def _load_text(path: str) -> str:
        if not path or not pathlib.Path(path).exists(): return ""
        return pathlib.Path(path).read_text(encoding="utf-8").strip()

    @staticmethod
    def _load_kpi_hints(path: str) -> Dict[str, Any]:
        if not path or not pathlib.Path(path).exists(): return {}
        try:
            if path.endswith((".yml", ".yaml")):
                return yaml.safe_load(pathlib.Path(path).read_text())
            if path.endswith(".json"):
                return json.loads(pathlib.Path(path).read_text())
            print("⚠️ KPI_HINTS_PATH must be JSON or YAML; ignoring.")
        except Exception as e:
            print(f"⚠️ Failed to load KPI hints: {e}")
        return {}

    @staticmethod
    def _fmt_dict(d: Dict[str, str]) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _parse(raw: str) -> Tuple[str, str]:
        subj = body = ""
        lines = [l for l in raw.strip().splitlines() if l]
        for i,l in enumerate(lines):
            if l.lower().startswith("subject:"):
                subj = l.split(":",1)[1].strip()
            if l.lower().startswith("body:"):
                body = "\n".join(lines[i+1:]).strip(); break
        for stop in ("Best,", "Regards,", "Kind regards"):  # strip stray sigs
            body = body.split(stop)[0].strip()
        return subj, body

    @staticmethod
    def _signature() -> str:
        return textwrap.dedent("""

            Cheers,
            Pranav Modi
            CEO · Possible Minds
            https://possibleminds.in  ·  LinkedIn: /in/pranav-modi-5a3a9b7
        """)

# ------------------------------ demo --------------------------------------
if __name__ == "__main__":
    composer = EmailComposer()
    sample_lead = {
        "name":     "Kristin Graves",
        "company":  "Fast Pace Health",
        "position": "VP of Talent",
        "email":    "kristin.graves@fastpacehealth.com"
    }
    email = composer.compose_email(sample_lead)
    if email:
        print("="*70)
        print("SUBJECT:", email["subject"])
        print("-"*70)
        print(email["body"])
