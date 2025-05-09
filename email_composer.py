# email_composer.py  ── v2  (implements “proof-first, arrow-subject, bullets, greeting & full links”)

import os, random, textwrap, json, pathlib, yaml
from typing import Dict, Tuple, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PRODUCT_DESC_PATH = "productdescription.txt"          # required
PROOF_POINTS_PATH = "proofpoints.txt"                 # optional
KPI_HINTS_PATH    = os.getenv("KPI_HINTS_PATH", "")   # optional YAML / JSON
DEFAULT_CALENDAR  = os.getenv(
    "CALENDAR_URL",
    "https://calendly.com/pranav-modi/15-minute-meeting",
)
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o")

# --------------------------------------------------------------------------- #
class EmailComposer:
    """
    Compose cold emails that follow the high-conversion pattern:
    • Arrow subject (≤ 9 words) with KPI outcome
    • Greeting line (“Hi <FirstName>,”)
    • Proof-point sentence
    • One-clause personalization anchor
    • Outcome-oriented bullets (bold benefit)
    • Dual CTA (Calendly + quick-reply digits)
    """

    def __init__(self) -> None:
        self.client         = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.product_desc   = self._load_text(PRODUCT_DESC_PATH)
        self.proof_points   = self._load_text(PROOF_POINTS_PATH).splitlines()
        self.kpi_hints      = self._load_kpi_hints(KPI_HINTS_PATH)

        self.system_prompt = textwrap.dedent(
            """
            You are an elite SDR writing ultra-concise, persuasive outbound emails.

            • SUBJECT: outcome-question with an arrow “→” (<= 9 words). Example:
              “Jane → Cut patient calls 40 %?”

            • BODY FORMAT (each part on its own line, exactly in this order):
              1. “Hi <FirstName>,”
              2. One-sentence proof metric from a similar company (use provided proof point).
              3. One clause personalisation about the prospect or their org (use data supplied).
              4. Bullets (3-4) — each begins with **bold benefit** then one-line mechanism.
              5. Provided CTA *verbatim* (no tweaks).

            • Use 2-3 realistic KPIs for the role:
                – If explicit KPI hints are provided, USE them.
                – Else infer logical KPIs for a US healthcare org.

            • Keep total words <= 120.
            • NO sign-off or closing; the script appends that.
            • Return EXACTLY the schema:

            Subject: <line>
            Body:
            <formatted body with line breaks>
            """
        )

    # ------------------------------------------------------------------ #
    def compose_email(
        self,
        lead: Dict[str, str],
        calendar_url: str = DEFAULT_CALENDAR,
        extra_context: str | None = None,
    ) -> Dict[str, str] | None:
        """Generate and return a dict {subject, body}."""

        if not self.product_desc:
            print("❗ productdescription.txt missing – aborting.")
            return None

        # ----- dynamic values ------------------------------------------------ #
        proof      = random.choice(self.proof_points) if self.proof_points else ""
        title      = lead.get("position", "").strip()
        first_name = lead.get("name", "").split()[0] if lead.get("name") else ""
        kpi_prompt = self.kpi_hints.get(title.upper(), "")
        cta        = (
            f"➡️ *Worth 15 min?* Pick a slot 👉 {calendar_url}\n"
            "Or reply **1** for yes / **2** for later."
        )

        # ----- assemble user prompt ----------------------------------------- #
        user_prompt = f"""
        === Lead ===
        {self._fmt_dict(lead)}

        === First name ===
        {first_name}

        === Product description ===
        {self.product_desc}

        === Proof point (use!) ===
        {proof}

        === KPI hints (may be empty) ===
        {kpi_prompt}

        === CTA (must appear exactly) ===
        {cta}

        {extra_context or ''}
        """

        try:
            rsp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.6,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            print("🔴 OpenAI error:", e)
            return None

        subject, body = self._parse(rsp.choices[0].message.content)
        body += self._signature()
        return {"subject": subject, "body": body}

    # ----------------------------- helpers --------------------------------- #
    @staticmethod
    def _load_text(path: str) -> str:
        if not path or not pathlib.Path(path).exists():
            return ""
        return pathlib.Path(path).read_text(encoding="utf-8").strip()

    @staticmethod
    def _load_kpi_hints(path: str) -> Dict[str, Any]:
        if not path or not pathlib.Path(path).exists():
            return {}
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
        """Split the model’s response into subject & body, stripping rogue sigs."""
        subj = body = ""
        lines = [l for l in raw.strip().splitlines() if l]
        for i, l in enumerate(lines):
            if l.lower().startswith("subject:"):
                subj = l.split(":", 1)[1].strip()
            if l.lower().startswith("body:"):
                body = "\n".join(lines[i + 1 :]).strip()
                break
        # remove any accidental sign-off from the model
        for stop in ("Best,", "Regards,", "Kind regards", "Cheers,"):
            body = body.split(stop)[0].strip()
        return subj, body

    @staticmethod
    def _signature() -> str:
        return textwrap.dedent(
            """

            Cheers,
            Pranav Modi
            CEO · Possible Minds
            https://possibleminds.in · https://www.linkedin.com/in/pranav-modi-5a3a9b7/
            """
        )

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    composer = EmailComposer()
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
