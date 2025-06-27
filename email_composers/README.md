# Email Composers Directory

This directory contains all the files used for email composition in the sales automation project.

## Main Composer Classes

### 1. **email_composer_warm.py** - `WarmEmailComposer`
- **Purpose**: Composes personal, founder-friendly emails inspired by Lily from Flex Capital
- **Style**: Less sales-y, more personal and curious
- **Subject Format**: "Possible Minds <> [company name]"
- **Features**:
  - Genuine curiosity about AI usage at the company
  - Brief founder introduction
  - Includes p.s. section with Precise Imaging case study
  - Warm, human tone with blank lines between paragraphs

### 2. **email_composer.py** - `EmailComposer`
- **Purpose**: High-conversion cold email composer following proven patterns
- **Style**: Professional, outcome-oriented with bullet points
- **Subject Format**: Arrow subject with KPI outcome (≤ 9 words), e.g., "Jane → Cut patient calls 40%?"
- **Features**:
  - Proof-point sentences from similar companies
  - One-clause personalization anchor
  - Bold benefit bullets with mechanisms
  - Dual CTA (Calendly + quick-reply digits)

### 3. **email_composer_alt_subject.py** - `AltSubjectEmailComposer`
- **Purpose**: Alternative composer with specific subject line format
- **Style**: Friendly founder-style outreach
- **Subject Format**: "[first-name], AI momentum at [company]?"
- **Features**:
  - Specific opening format about AI leverage
  - Three required talking points about AI adoption
  - Embedded leadership quotes (Sundar Pichai, Satya Nadella, Trey Lowe)
  - Mentions Precise Imaging deployment

## Supporting Files

### **composer_instance.py**
- Creates a shared instance of `WarmEmailComposer` for use across the application
- Default composer used by the email sending system

### **productdescription.txt**
- Contains the product description used by all composers
- Describes the AI chatbot solution capabilities
- Used as context for email generation

### **proofpoints.txt**
- Contains proof points and success metrics from Precise Imaging
- Used to add credibility to emails
- Randomly selected for inclusion in emails

## Usage

All composers follow the same interface:
```python
composer = EmailComposer()  # or WarmEmailComposer or AltSubjectEmailComposer
email_content = composer.compose_email(lead_data, calendar_url, extra_context)
# Returns: {"subject": "...", "body": "..."}
```

## Integration

These composers are used by:
- `send_emails.py` - For bulk email sending
- `app/services/email_service.py` - For web interface email composition
- Various dashboard components for email generation 