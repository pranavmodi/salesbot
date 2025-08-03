import sys
import os
import logging

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# Set environment variables for WeasyPrint library paths on macOS
if os.name != 'nt':  # Not Windows
    # Add brew library paths for WeasyPrint dependencies
    library_paths = [
        '/usr/local/lib',
        '/usr/local/opt/glib/lib',
        '/usr/local/opt/pango/lib',
        '/usr/local/opt/cairo/lib',
        '/usr/local/opt/gdk-pixbuf/lib'
    ]
    
    existing_path = os.environ.get('DYLD_LIBRARY_PATH', '')
    if existing_path:
        os.environ['DYLD_LIBRARY_PATH'] = ':'.join(library_paths) + ':' + existing_path
    else:
        os.environ['DYLD_LIBRARY_PATH'] = ':'.join(library_paths)

# Configure logging with rotating file handler for 48-hour activity
import logging.handlers
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Create log file path
log_file = os.path.join(log_dir, 'salesbot_activity.log')

# Set up the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Clear any existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Console handler (for development/debugging)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# Rotating file handler (keeps last 48 hours)
# Using TimedRotatingFileHandler with daily rotation and keeping 2 files (48 hours)
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=log_file,
    when='midnight',  # Rotate at midnight
    interval=1,       # Every 1 day
    backupCount=2,    # Keep 2 backup files (today + yesterday = 48 hours)
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

# Reduce werkzeug HTTP request logging noise
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Log startup
logging.info("=== SalesBot Application Starting ===")
logging.info(f"Log file: {log_file}")
logging.info(f"Log rotation: Daily at midnight, keeping 48 hours of logs")

app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug) 