from functools import wraps
from flask import session, redirect, url_for, request


def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # Store the original URL to redirect back after login
            session['next_url'] = request.url
            return redirect(url_for('main.login_page'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get the current logged-in user from session."""
    return session.get('user')


def is_logged_in():
    """Check if a user is currently logged in."""
    return 'user' in session