# Email Composers Directory

This directory contains all the files used for email composition in the sales automation project.

## Main Composer Classes

### 1. **email_composer_deep_research.py** - `DeepResearchEmailComposer` ⭐ DEFAULT
- **Purpose**: Research-backed, highly personalized emails using deep company research data
- **Style**: Strategic, insight-driven outreach that demonstrates business understanding
- **Subject Format**: "[Company] → [Specific Outcome/Challenge]?" (≤ 50 characters)
- **Features**:
  - Leverages AI company research for specific pain points and business insights
  - References actual business challenges from research data
  - Industry-specific personalization with credible business context
  - Strategic solution positioning based on company intelligence
  - **Auto-triggers research** for companies when no data is available
  - P.S. section with relevant case study reference

### 2. **email_composer_warm.py** - `WarmEmailComposer`
- **Purpose**: Composes personal, founder-friendly emails inspired by Lily from Flex Capital
- **Style**: Less sales-y, more personal and curious
- **Subject Format**: "Possible Minds <> [company name]"
- **Features**:
  - Genuine curiosity about AI usage at the company
  - Brief founder introduction
  - Includes p.s. section with Precise Imaging case study
  - Warm, human tone with blank lines between paragraphs

### 3. **email_composer.py** - `EmailComposer`
- **Purpose**: High-conversion cold email composer following proven patterns
- **Style**: Professional, outcome-oriented with bullet points
- **Subject Format**: Arrow subject with KPI outcome (≤ 9 words), e.g., "Jane → Cut patient calls 40%?"
- **Features**:
  - Proof-point sentences from similar companies
  - One-clause personalization anchor
  - Bold benefit bullets with mechanisms
  - Dual CTA (Calendly + quick-reply digits)

### 4. **email_composer_alt_subject.py** - `AltSubjectEmailComposer`
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
- Note: Campaign system now defaults to `DeepResearchEmailComposer` for new campaigns

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
- `app/services/campaign_scheduler.py` - For campaign email automation
- Various dashboard components for email generation

## Deep Research Integration

The `DeepResearchEmailComposer` automatically integrates with the deep research system:
- Queries the `companies` table for research data based on contact's company name
- Uses `research_step_1_basic` or `company_research` fields when available
- **Auto-triggers research** when no company record exists or research data is missing
- Creates new company records and performs AI research automatically
- Falls back to general industry insights only when auto-research fails
- Leverages the AI research service findings to create highly targeted emails

### Auto-Research Behavior:
1. **Company Not Found**: Creates company record → Triggers AI research → Uses results
2. **Company Exists, No Research**: Triggers AI research for existing company → Uses results  
3. **Research Available**: Uses existing research data immediately
4. **Research Fails**: Falls back to general industry insights

This ensures maximum personalization by automatically building your research database as you send campaigns!

### Configuration:
- **Environment Variable**: Set `AUTO_RESEARCH_ENABLED=false` to disable auto-triggering globally
- **Per-Call Control**: Pass `auto_research=False` to `compose_email()` to disable for specific emails
- **Default Behavior**: Auto-research is enabled by default for maximum personalization 