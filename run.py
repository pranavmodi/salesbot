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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce werkzeug HTTP request logging noise
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug) 