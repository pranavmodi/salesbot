# Perplexity Sonar Deep Research Integration

This document describes the integration of Perplexity's Sonar Deep Research API as a provider option for the LLM Deep Research system.

## Overview

Perplexity Sonar Deep Research has been added as a third provider option alongside Claude and OpenAI, offering:

- **Expert-level research capabilities** with exhaustive web searches
- **Real-time web information access** with automatic source attribution
- **Comprehensive business intelligence** gathering for B2B sales purposes
- **Cost-effective pricing** compared to OpenAI's Deep Research API

## Setup

### 1. API Key Configuration

Add your Perplexity API key to the `.env` file:

```bash
# Add your Perplexity API key here for Sonar deep research
PERPLEXITY_API_KEY=your-perplexity-api-key-here
```

You can obtain an API key from [Perplexity's Developer Platform](https://docs.perplexity.ai).

### 2. Provider Selection

When starting deep research, you can now select Perplexity as the provider:

1. Open the Deep Research modal for any company
2. In the provider dropdown, select "Perplexity (Sonar Deep Research)"
3. Click "Start Deep Research"

## Technical Details

### API Integration

- **Model**: `sonar-deep-research`
- **Base URL**: `https://api.perplexity.ai`
- **Web Search**: Enabled with `search_mode: "web"`
- **Reasoning**: High-effort reasoning with `reasoning_effort: "high"`
- **Max Tokens**: 8,000 tokens for comprehensive reports

### Features Used

- **Web Search Mode**: Conducts real-time web searches for current information
- **Source Attribution**: Automatically includes citations and URLs
- **High Reasoning**: Uses maximum reasoning capability for detailed analysis
- **Business Intelligence Focus**: Specialized prompts for B2B sales intelligence

### Cost Estimation

- **Estimated Cost**: ~$0.20 per research request
- **Compared to**: OpenAI ($0.50), Claude ($0.10)
- **Value**: Balance of comprehensive research and reasonable pricing

## Research Process

The Perplexity integration follows the same 3-step research workflow:

1. **Step 1 - Basic Research**: Deep web research using Perplexity Sonar
2. **Step 2 - Strategic Analysis**: Strategic analysis using the same provider
3. **Step 3 - Report Generation**: Final report generation with comprehensive insights

## Monitoring and Safety

### API Call Tracking

The system includes comprehensive monitoring of Perplexity API calls:

- **Cost Tracking**: Estimated costs per request
- **Usage Monitoring**: Call frequency and patterns
- **Error Handling**: Detailed error diagnosis and logging
- **Safety Limits**: Rate limiting and spend monitoring

### Error Handling

Comprehensive error handling for Perplexity-specific issues:

- **Authentication Errors**: API key validation
- **Rate Limits**: Automatic detection and reporting
- **Model Availability**: Fallback handling if model is unavailable
- **Request Validation**: Parameter validation and error reporting

## Usage Examples

### Selecting Perplexity Provider

```javascript
// Provider selection in the UI
const provider = document.getElementById('llmProviderSelect').value; // 'perplexity'
```

### API Request Example

```python
# Internal API usage (handled automatically)
from deepresearch.llm_deep_research_service import LLMDeepResearchService

service = LLMDeepResearchService()
result = service.research_company_deep(
    company_name="Example Corp",
    company_domain="example.com",
    provider="perplexity",
    company_id=123
)
```

## Benefits

### 1. Real-Time Web Research
- Accesses current web information
- Provides up-to-date company data
- Includes recent news and developments

### 2. Source Attribution
- Automatic citation of sources
- URLs for verification
- Transparent research process

### 3. Comprehensive Analysis
- Deep web searches across multiple sources
- Strategic business intelligence
- Actionable insights for sales teams

### 4. Cost Efficiency
- Moderate pricing between Claude and OpenAI
- Good value for comprehensive research
- Transparent cost tracking

## Best Practices

1. **Use for Current Information**: Leverage Perplexity when you need the most current company data
2. **Review Sources**: Check the provided citations for accuracy
3. **Monitor Costs**: Keep track of usage through the monitoring system
4. **Compare Results**: Test different providers to find the best fit for your needs

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Check that `PERPLEXITY_API_KEY` is set correctly
2. **Model Not Found**: Verify that your API key has access to the Sonar Deep Research model
3. **Rate Limits**: Monitor usage and implement delays if needed
4. **No Results**: Check network connectivity and API status

### Support

- Check logs for detailed error messages
- Use the monitoring script to track API calls
- Review Perplexity's documentation for API updates
- Contact support if issues persist

## Integration Status

✅ **Completed Features:**
- API client integration with OpenAI-compatible interface
- Provider selection in UI dropdown
- Comprehensive error handling and logging
- Cost estimation and monitoring
- 3-step research workflow support
- Monitoring script integration

🔄 **Future Enhancements:**
- Advanced search filtering options
- Custom domain restrictions
- Batch processing capabilities
- Enhanced source analysis

---

For more information about Perplexity's capabilities, visit their [official documentation](https://docs.perplexity.ai).