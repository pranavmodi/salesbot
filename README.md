# Sales Email Automation Script

This Python script reads lead information and personalized messages from a CSV file (`leads_with_messages.csv`) and sends cold emails using SMTP.

## Setup

1.  **Clone the repository (if applicable).**
2.  **Create a `.env` file:**
    In the root directory of the project, create a file named `.env`. Copy the following content into it and **replace the placeholder values with your actual SMTP server details, sender email credentials, and desired CSV file path**:
    ```env
    SMTP_HOST="smtp.example.com" # e.g., "smtp.gmail.com" or "smtp.office365.com"
    SMTP_PORT=587 # Common port for TLS (usually 587 for TLS, 465 for SSL)
    SENDER_EMAIL="your_email@example.com"
    SENDER_PASSWORD="your_password" # Use an App Password if using Gmail with 2FA
    
    # Path to the CSV file containing leads (defaults to 'leads_with_messages.csv' if omitted)
    CSV_FILE_PATH="leads_with_messages.csv"
    ```
    *   To use the provided sample test file, change the last line to: `CSV_FILE_PATH="test_leads.csv"`
    **Note:** This file is listed in `.gitignore` to prevent accidental commits of sensitive information.

3.  **Configure Non-Sensitive Settings (Optional):**
    You can adjust the default email subject line in the `config.py` file:
    ```python
    # Non-sensitive Email Settings
    EMAIL_SUBJECT = "Following up"
    ```

4.  **Prepare your leads file:**
    Ensure your CSV file (specified by `CSV_FILE_PATH` in `.env` or defaulting to `leads_with_messages.csv`) exists and has at least the following columns:
    *   `First Name`
    *   `Work Email`
    *   `LinkedIn Message` (This will be used as the email body)
    
    A sample file `test_leads.csv` is included for testing purposes. It contains one row sending an email to `pranav.modi@gmail.com`.

5.  **Install dependencies:**
    This script requires the `python-dotenv` library to load environment variables. Install it using pip:
    ```bash
    pip install -r requirements.txt
    ```
    *(Consider using a virtual environment for managing dependencies: `python -m venv venv`, `source venv/bin/activate` (or `venv\Scripts\activate` on Windows), then `pip install -r requirements.txt`)*

## Running the Script

Execute the script from your terminal (ensure your virtual environment is activated if you are using one):

```bash
python send_emails.py
```

The script will:
*   Load configuration from `.env` and `config.py`.
*   Determine the CSV file to use based on the `CSV_FILE_PATH` environment variable (defaulting to `leads_with_messages.csv`).
*   Read the specified CSV file.
*   Iterate through the rows.
*   Attempt to send an email to each valid recipient using the provided message and personalized subject line.

## Important Considerations

*   **Security:** Keep your `.env` file secure and do not commit it to version control.
*   **Rate Limiting:** Email providers often have sending limits. The script includes a basic `time.sleep(1)` delay, but you might need more sophisticated handling (e.g., exponential backoff, checking provider limits) depending on your provider and volume.
*   **Error Handling:** The script includes basic error handling for sending emails and loading configuration. You might want to add more robust logging (e.g., writing errors to a file) and retries for failed sends.
*   **Personalization:** Enhance personalization further in `send_emails.py` if needed.
*   **Unsubscribe/Opt-out:** Ensure your cold emailing practices comply with regulations like CAN-SPAM or GDPR, which typically require an unsubscribe mechanism. This script does **not** currently include one.
*   **Email Validation:** Consider adding more robust email address format validation before attempting to send. 