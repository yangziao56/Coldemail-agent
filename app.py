"""Flask web application for Cold Email Generator."""

import os
import tempfile
from pathlib import Path
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from src.email_agent import (
    SenderProfile,
    ReceiverProfile,
    generate_email,
    extract_profile_from_pdf,
)
from src.web_scraper import extract_person_profile_from_web

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'coldemail-secret-key-2024')

# Password for accessing the app
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'gogogochufalo')

# Store uploaded sender profile temporarily
sender_profile_cache = {}


def login_required(f):
    """Decorator to require login for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Render the main page."""
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    if request.method == 'GET':
        if session.get('authenticated'):
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # Handle POST - check for both JSON and form data
    if request.is_json:
        data = request.get_json()
        password = data.get('password', '')
    else:
        password = request.form.get('password', '')
    
    if password == APP_PASSWORD:
        session['authenticated'] = True
        session.permanent = True
        if request.is_json:
            return jsonify({'success': True})
        return redirect(url_for('index'))
    else:
        if request.is_json:
            return jsonify({'error': 'Incorrect password'}), 401
        return render_template('login.html', error='Incorrect password')


@app.route('/logout')
def logout():
    """Handle logout."""
    session.pop('authenticated', None)
    return redirect(url_for('index'))


@app.route('/api/upload-sender-pdf', methods=['POST'])
@login_required
def upload_sender_pdf():
    """Upload and parse sender PDF resume."""
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400
    
    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400
    
    try:
        # Save to temp file and extract profile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_file.save(tmp.name)
            profile = extract_profile_from_pdf(Path(tmp.name))
            os.unlink(tmp.name)  # Clean up temp file
        
        # Cache the extracted profile
        session_id = request.form.get('session_id', 'default')
        sender_profile_cache[session_id] = {
            'name': profile.name,
            'raw_text': profile.raw_text,
            'education': profile.education,
            'experiences': profile.experiences,
            'skills': profile.skills,
            'projects': profile.projects,
        }
        
        return jsonify({
            'success': True,
            'profile': sender_profile_cache[session_id]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search-receiver', methods=['POST'])
@login_required
def search_receiver():
    """Search for receiver information from the web."""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    field = data.get('field', '').strip()
    
    if not name:
        return jsonify({'error': 'Receiver name is required'}), 400
    if not field:
        return jsonify({'error': 'Receiver field is required'}), 400
    
    try:
        scraped_info = extract_person_profile_from_web(
            name=name,
            field=field,
            max_pages=3,
        )
        
        return jsonify({
            'success': True,
            'profile': {
                'name': scraped_info.name,
                'field': scraped_info.field,
                'education': scraped_info.education,
                'experiences': scraped_info.experiences,
                'skills': scraped_info.skills,
                'projects': scraped_info.projects,
                'sources': scraped_info.sources,
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-email', methods=['POST'])
@login_required
def api_generate_email():
    """Generate cold email based on sender and receiver profiles."""
    data = request.get_json()
    
    try:
        # Get sender profile
        sender_data = data.get('sender', {})
        sender = SenderProfile(
            name=sender_data.get('name', ''),
            raw_text=sender_data.get('raw_text', ''),
            education=sender_data.get('education', []),
            experiences=sender_data.get('experiences', []),
            skills=sender_data.get('skills', []),
            projects=sender_data.get('projects', []),
            motivation=sender_data.get('motivation', ''),
            ask=sender_data.get('ask', ''),
        )
        
        # Get receiver profile
        receiver_data = data.get('receiver', {})
        receiver = ReceiverProfile(
            name=receiver_data.get('name', ''),
            raw_text=receiver_data.get('raw_text', ''),
            education=receiver_data.get('education', []),
            experiences=receiver_data.get('experiences', []),
            skills=receiver_data.get('skills', []),
            projects=receiver_data.get('projects', []),
            context=receiver_data.get('context', ''),
        )
        
        # Get goal
        goal = data.get('goal', '')
        if not goal:
            return jsonify({'error': 'Goal is required'}), 400
        
        # Generate email
        email_text = generate_email(sender, receiver, goal)
        
        return jsonify({
            'success': True,
            'email': email_text
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Make sure GEMINI_API_KEY is set
    if not os.environ.get('GEMINI_API_KEY') and not os.environ.get('GOOGLE_API_KEY'):
        print("Warning: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
