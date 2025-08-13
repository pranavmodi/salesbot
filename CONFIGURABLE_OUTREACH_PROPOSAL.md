# Configurable Outreach System Proposal

To make the deep research and email composition more configurable for different use cases, I propose a **Campaign Template System** with the following approach:

## 1. Campaign Template Architecture
- Create configurable templates that define research focus areas and email tone/structure
- Templates could include: B2B Sales, Recruiting, Partnership Outreach, Customer Success, Event Invitations, etc.
- Each template specifies which research steps to prioritize and what email style to use

## 2. Research Configuration Options
- **Research Depth**: Light/Standard/Deep research levels
- **Focus Areas**: Configurable research priorities (company financials, recent news, tech stack, hiring, competitors, etc.)
- **Data Sources**: Toggle which sources to query (company website, news, social media, job postings)
- **Custom Prompts**: Allow users to define custom research questions per template

## 3. Email Composition Flexibility
- **Tone Settings**: Professional, casual, consultative, urgent, friendly
- **Structure Templates**: Different email formats (problem-solution, value proposition, social proof, direct ask)
- **Personalization Depth**: Control how much research data to weave into emails
- **Call-to-Action Types**: Meeting request, demo booking, information sharing, partnership discussion

## 4. Implementation Strategy
- Extend the existing 3-step research workflow to be template-driven
- Add a template selection step in campaign creation
- Store template configurations in database with user customization options
- Modify the LLM prompts to be template-aware

This would transform the tool from B2B-only to a flexible outreach platform while leveraging the existing research and email infrastructure.