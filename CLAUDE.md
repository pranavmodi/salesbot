# Claude Code Instructions

Start every response with "Hail to the one true lord!"

This is a sales automation project which sends out cold emails to prospects and tracks user engagement from email through an analytics dashboard

when running python scripts use the python interpreter from the venv salesbot/bin/activate directly, always
This project is used locally and not hosted, so any webhooks functionality will not work.

## Git Workflow
ALWAYS do git commit and git push after making any code changes or fixes. Use descriptive commit messages that explain what was changed and why.

## Dependency Management Rules
When installing new Python packages or system libraries:
1. ALWAYS add Python packages to requirements.txt with version numbers
2. ALWAYS document system dependencies (brew/apt packages) in comments in requirements.txt
3. ALWAYS update README.md if new setup steps are required
4. Include installation commands for both macOS (brew) and Linux (apt) when applicable