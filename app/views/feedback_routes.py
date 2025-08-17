from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.auth import login_required, get_current_user
from app.models.feedback import Feedback
import logging

feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')

@feedback_bp.route('/')
@login_required
def feedback_form():
    """Display feedback form for users."""
    return render_template('feedback/form.html')

@feedback_bp.route('/submit', methods=['POST'])
@login_required
def submit_feedback():
    """Submit user feedback."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        message = data.get('message', '').strip()
        category = data.get('category', 'general').strip()

        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400

        # Validate category
        valid_categories = ['general', 'bug', 'feature', 'other']
        if category not in valid_categories:
            category = 'general'

        # Create feedback
        feedback = Feedback.create(
            user_id=user['id'],
            user_email=user['email'],
            user_name=user['name'],
            tenant_id=user['tenant_id'],
            message=message,
            category=category
        )

        if feedback:
            logging.getLogger(__name__).info(f"Feedback submitted by user {user['email']}: {category}")
            return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to submit feedback'}), 500

    except Exception as e:
        logging.getLogger(__name__).error(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/thank-you')
@login_required
def thank_you():
    """Thank you page after feedback submission."""
    return render_template('feedback/thank_you.html')