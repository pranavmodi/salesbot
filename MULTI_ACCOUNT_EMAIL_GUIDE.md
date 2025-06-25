# Multi-Account Email Configuration Guide

## Overview

Your salesbot now supports multiple email accounts! You can configure multiple email addresses and choose which one to use for sending emails. This is useful for:

- Using different email addresses for different campaigns
- Load balancing across multiple accounts to avoid rate limits
- Separating business units or brands
- Having backup accounts in case one goes down

## Configuration

### JSON Format (Recommended)

The new configuration uses a JSON array in your `.env2` file. Here's the format:

```bash
EMAIL_ACCOUNTS=[
  {
    "name": "primary",
    "email": "your-email@domain.com",
    "password": "your-password",
    "smtp_host": "smtp.provider.com",
    "smtp_port": 465,
    "smtp_use_ssl": true,
    "imap_host": "imap.provider.com",
    "imap_port": 993,
    "imap_use_ssl": true,
    "is_default": true
  }
]
```

### Multiple Accounts Example

```bash
EMAIL_ACCOUNTS=[
  {
    "name": "primary",
    "email": "sales@yourcompany.com",
    "password": "password123",
    "smtp_host": "smtppro.zoho.in",
    "smtp_port": 465,
    "smtp_use_ssl": true,
    "imap_host": "imap.zoho.com",
    "imap_port": 993,
    "imap_use_ssl": true,
    "is_default": true
  },
  {
    "name": "secondary",
    "email": "marketing@yourcompany.com", 
    "password": "password456",
    "smtp_host": "smtppro.zoho.in",
    "smtp_port": 465,
    "smtp_use_ssl": true,
    "imap_host": "imap.zoho.com",
    "imap_port": 993,
    "imap_use_ssl": true,
    "is_default": false
  },
  {
    "name": "gmail_backup",
    "email": "backup@gmail.com",
    "password": "gmail_app_password",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_use_ssl": false,
    "imap_host": "imap.gmail.com",
    "imap_port": 993,
    "imap_use_ssl": true,
    "is_default": false
  }
]
```

## Account Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier for the account |
| `email` | Yes | Email address |
| `password` | Yes | Email password or app password |
| `smtp_host` | Yes | SMTP server hostname |
| `smtp_port` | Yes | SMTP port (usually 465 for SSL, 587 for TLS) |
| `smtp_use_ssl` | Yes | Whether to use SSL (true for port 465, false for port 587) |
| `imap_host` | Yes | IMAP server hostname |
| `imap_port` | Yes | IMAP port (usually 993) |
| `imap_use_ssl` | Yes | Whether to use SSL for IMAP (usually true) |
| `is_default` | Yes | Whether this is the default account (only one should be true) |

## Provider-Specific Settings

### Zoho Mail
```json
{
  "smtp_host": "smtppro.zoho.in",  # or "smtp.zoho.com" for international
  "smtp_port": 465,
  "smtp_use_ssl": true,
  "imap_host": "imap.zoho.com",
  "imap_port": 993,
  "imap_use_ssl": true
}
```

### Gmail
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,  # or 465 for SSL
  "smtp_use_ssl": false,  # true if using port 465
  "imap_host": "imap.gmail.com", 
  "imap_port": 993,
  "imap_use_ssl": true
}
```

### Outlook/Hotmail
```json
{
  "smtp_host": "smtp-mail.outlook.com",
  "smtp_port": 587,
  "smtp_use_ssl": false,
  "imap_host": "outlook.office365.com",
  "imap_port": 993,
  "imap_use_ssl": true
}
```

## Usage

### API Endpoints

#### Get Available Accounts
```bash
GET /api/email/accounts
```

Response:
```json
{
  "success": true,
  "accounts": [
    {
      "name": "primary",
      "email": "sales@yourcompany.com",
      "is_default": true
    },
    {
      "name": "secondary", 
      "email": "marketing@yourcompany.com",
      "is_default": false
    }
  ]
}
```

#### Send Email with Specific Account
```bash
POST /api/send_email
```

Form data:
- `recipient_email`: Recipient's email
- `recipient_name`: Recipient's name
- `preview_subject`: Email subject
- `preview_body`: Email body
- `account_name`: (Optional) Name of account to use

#### Test Account Configuration
```bash
POST /api/email/accounts/{account_name}/test
```

### Python Usage

```python
from app.services.email_service import EmailService

# Send with default account
EmailService.send_email_with_account(
    recipient_email="customer@example.com",
    recipient_name="John Doe", 
    subject="Hello",
    body="This is a test email"
)

# Send with specific account
EmailService.send_email_with_account(
    recipient_email="customer@example.com",
    recipient_name="John Doe",
    subject="Hello", 
    body="This is a test email",
    account_name="secondary"
)

# Get available accounts
accounts = EmailService.get_available_accounts()
```

### Command Line Usage

```python
# In send_emails.py
from send_emails import send_email

# Send with default account
send_email("customer@example.com", "Subject", "Body content")

# Send with specific account  
send_email("customer@example.com", "Subject", "Body content", account_name="secondary")
```

## Migration from Single Account

Your existing single-account configuration will continue to work as a fallback. The system will:

1. First try to load accounts from `EMAIL_ACCOUNTS`
2. If that fails, fall back to the legacy `SENDER_EMAIL`, `SENDER_PASSWORD`, etc.

This ensures backward compatibility while you transition to the new system.

## Best Practices

1. **Security**: Use app passwords instead of regular passwords when possible
2. **Default Account**: Always have one account marked as default
3. **Testing**: Test each account configuration using the test endpoint
4. **Rate Limits**: Distribute sending across multiple accounts to avoid rate limits
5. **Backup**: Keep at least one backup account configured

## Troubleshooting

### Account Not Found
- Check that the account name is spelled correctly
- Verify the account exists in your `EMAIL_ACCOUNTS` configuration

### Authentication Failed
- Verify email and password are correct
- For Gmail, ensure you're using an app password, not your regular password
- Check if 2FA is enabled and you need an app-specific password

### Connection Failed
- Verify SMTP/IMAP hosts and ports are correct
- Check if your email provider requires specific security settings
- Ensure your server can reach the email provider's servers

### JSON Parse Error
- Validate your JSON syntax using an online JSON validator
- Check for missing commas, quotes, or brackets
- Ensure boolean values are lowercase (`true`/`false`, not `True`/`False`)

## Support

If you encounter issues:
1. Check the application logs for detailed error messages
2. Test individual accounts using the test endpoint
3. Verify your JSON configuration syntax
4. Ensure your email provider settings are correct 