# Deep Research System

A modular company research system that uses AI to analyze companies and generate strategic recommendations for sales outreach.

## 🏗️ Refactored Architecture

The original monolithic `deep_research_companies.py` (618 lines) has been refactored into a clean, modular architecture:

```
deepresearch/
├── __init__.py                 # Package initialization and exports
├── database_service.py         # Database operations (~150 lines)
├── ai_research_service.py      # OpenAI API interactions (~120 lines)
├── report_generator.py         # Markdown report generation (~80 lines)
├── company_researcher.py       # Main orchestrator (~180 lines)
├── cli.py                      # Command line interface (~90 lines)
├── deep_research_companies.py  # Legacy entry point (backward compatibility)
└── reports/                    # Generated markdown reports
```

## 📋 Module Responsibilities

### 1. DatabaseService (`database_service.py`)
- Extract unique companies from contacts table
- Manage company records (CRUD operations)
- Handle database connections and transactions
- Query existing companies to avoid duplicates

### 2. AIResearchService (`ai_research_service.py`)
- Company research using OpenAI GPT models
- Strategic analysis generation
- Business insights and recommendations
- Pain point identification and solution mapping

### 3. ReportGenerator (`report_generator.py`)
- Markdown report creation and formatting
- File system operations for report storage
- Report directory management
- Company name sanitization for filenames

### 4. CompanyResearcher (`company_researcher.py`)
- Main orchestrator coordinating all services
- Batch processing workflow management
- Single company research operations
- Progress tracking and error handling

### 5. CLI (`cli.py`)
- Command line argument parsing
- User interface and workflow coordination
- Dry-run capabilities
- Error handling and user feedback

## 🚀 Usage

### Command Line Interface
The CLI interface remains exactly the same as before:

```bash
# Research all new companies
python -m deepresearch.cli

# Research with limits and delays
python -m deepresearch.cli --max-companies 10 --delay 3

# Research a specific company by ID
python -m deepresearch.cli --company-id 123

# Dry run to see what would be processed
python -m deepresearch.cli --dry-run --max-companies 5

# Skip report generation (research only)
python -m deepresearch.cli --no-reports

# Legacy entry point (still works)
python deepresearch/deep_research_companies.py --help
```

### Programmatic Usage
You can now import and use individual services:

```python
from deepresearch import CompanyResearcher, DatabaseService, AIResearchService

# Use the main orchestrator
researcher = CompanyResearcher()
researcher.process_companies(max_companies=5)

# Use individual services
db_service = DatabaseService()
companies = db_service.get_unique_companies_from_contacts()

ai_service = AIResearchService()
research = ai_service.research_company("Example Corp", "example.com")
```

## 🎯 Benefits of Refactoring

### 1. **Single Responsibility Principle**
- Each module has one clear purpose
- Easier to understand and maintain
- Cleaner dependencies

### 2. **Better Testability**
- Individual components can be unit tested
- Mock dependencies for isolated testing
- Easier to debug specific functionality

### 3. **Improved Maintainability**
- Changes to one aspect don't affect others
- Easier to extend functionality
- Clear separation of concerns

### 4. **Enhanced Reusability**
- Services can be used independently
- Better code organization
- Easier to integrate with other systems

### 5. **Cleaner Code**
- Reduced file size (150-180 lines per module vs 618 lines)
- Better organization
- More readable and maintainable

## 📊 Generated Reports

Reports are generated in the `deepresearch/reports/` directory with the following structure:

```markdown
# Deep Research Analysis: [Company Name]

## Company Research Analysis
- Snapshot (3-sentence overview)
- Source Harvest (recent facts and citations)
- Signals → Pain Hypotheses (by business function)
- Top-3 Burning Problems (ranked pain points)
- Solution Hooks & Message Angles (AI/LLM solutions)

## Strategic Analysis
- Executive Summary
- Industry Position & Competitive Landscape  
- Strategic Recommendations (3-5 high-impact items)
- AI Agents: Strategic Priority Assessment
- Implementation Roadmap (12-18 months)
- Risk Assessment & Mitigation
```

## 🔧 Environment Setup

Ensure you have the required environment variables:

```bash
DATABASE_URL=postgresql://user:pass@localhost/salesbot
OPENAI_KEY=sk-...
OPENAI_MODEL=o3  # or gpt-4, gpt-3.5-turbo
```

## 📈 Future Enhancements

The modular architecture makes it easy to add:

- **Caching Service**: Cache research results to avoid duplicate API calls
- **Async Processing**: Parallel company research for better performance  
- **Multiple AI Providers**: Support for Claude, Gemini, etc.
- **Export Formats**: PDF, Word, JSON export options
- **Web Interface**: Flask/FastAPI web UI for the research system
- **Notification Service**: Email/Slack notifications on completion

## 🔄 Migration Notes

- **Backward Compatibility**: The original `deep_research_companies.py` still works
- **Same CLI Interface**: All command-line arguments work exactly the same
- **Same Output**: Reports and database entries are identical
- **No Breaking Changes**: Existing workflows continue to work

This refactoring maintains 100% backward compatibility while providing a much cleaner, more maintainable codebase for future development. 