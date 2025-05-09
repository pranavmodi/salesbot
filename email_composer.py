import os
from typing import Dict
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the path for the product description file
PRODUCT_DESC_PATH = "productdescription.txt"

class EmailComposer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_KEY'))
        self.product_description = self._load_product_description()
        
        # Default system prompt for email composition
        self.default_system_prompt = """You are an expert sales development representative.
Your task is to write personalized, engaging cold emails that are:
1. Professional and courteous
2. Concise and to the point
3. Focused on the value proposition derived from the provided product description
4. Natural and conversational
5. Not overly salesy or pushy

The email should have:
- A compelling subject line
- A personalized opening
- A clear value proposition (use the provided product description)
- A specific call to action"""

    def _load_product_description(self) -> str:
        """Loads the product description from the file."""
        try:
            with open(PRODUCT_DESC_PATH, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Warning: Product description file not found at {PRODUCT_DESC_PATH}. Emails may lack specific product details.")
            return "" # Return empty string if file not found
        except Exception as e:
            print(f"Error reading product description file: {e}")
            return "" # Return empty string on other errors

    def compose_email(
        self,
        lead_info: Dict[str, str],
        custom_context: str = None
    ) -> Dict[str, str]:
        """
        Compose a personalized email using GPT-4.
        
        Args:
            lead_info: Dictionary containing lead information (name, company, etc.)
            custom_context: Optional additional context or specific instructions
            
        Returns:
            Dict containing 'subject' and 'body' of the email
        """
        if not self.product_description:
            print("Warning: Cannot compose email without product description.")
            return None
            
        # Construct the prompt
        prompt = f"""Please write a cold email for the following lead:

Lead Information:
{self._format_lead_info(lead_info)}

Product Description to use for the sales pitch:
{self.product_description}

{custom_context if custom_context else ''}

Format the response as:
Subject: [Your subject line]

[Your email body]"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.default_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse the response
            content = response.choices[0].message.content
            subject, body = self._parse_email_response(content)
            
            return {
                'subject': subject,
                'body': body
            }
            
        except Exception as e:
            print(f"Error composing email: {e}")
            return None

    def _format_lead_info(self, lead_info: Dict[str, str]) -> str:
        """Format lead information for the prompt."""
        return "\n".join(f"- {key}: {value}" for key, value in lead_info.items())

    def _parse_email_response(self, content: str) -> tuple:
        """Parse the email response into subject and body."""
        lines = content.strip().split('\n')
        
        # Find the subject line
        subject = ""
        body_start = 0
        for i, line in enumerate(lines):
            if line.lower().startswith('subject:'):
                subject = line.replace('Subject:', '').strip()
                body_start = i + 1
                break
        
        # Join the rest as body
        body = '\n'.join(lines[body_start:]).strip()
        
        return subject, body

# Example usage
if __name__ == "__main__":
    composer = EmailComposer()
    
    # Example lead information
    lead_info = {
        "name": "John Smith",
        "company": "Tech Corp",
        "position": "CTO",
        "company_info": "AI-focused startup with 50+ employees"
    }
    
    # Test email composition
    email = composer.compose_email(lead_info)
    if email:
        print("Subject:", email['subject'])
        print("\nBody:", email['body']) 