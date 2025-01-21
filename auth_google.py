from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from authlib.integrations.flask_client import OAuth
import os

auth_bp = Blueprint('auth', __name__)

oauth = OAuth()
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v2/',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Hardcoded credentials for testing (replace this with a database in production)
VALID_CREDENTIALS = {
    "hwalee": "donotshare",
}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle ID/password login and Google OAuth login.
    """
    if request.method == 'POST':
        # Capture the submitted username and password
        username = request.form.get('username')
        password = request.form.get('password')

        # Debug: Print the captured username and password to the console
        print(f"Username: {username}, Password: {password}")

        # Validate credentials
        if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
            session['user'] = {'username': username}  # Save user info in session
            return redirect(url_for('auth.index'))
        else:
            flash('Invalid username or password')  # Display error message
            return render_template('login.html')  # Re-render login page with error

    # Render login page for GET request
    return render_template('login.html')

@auth_bp.route('/google-login')
def google_login():
    """
    Redirect to Google login.
    """
    return google.authorize_redirect(url_for('auth.callback', _external=True))

@auth_bp.route('/callback')
def callback():
    """
    Handle Google OAuth callback.
    """
    try:
        google.authorize_access_token()
        user_info = google.get('userinfo').json()
        email = user_info.get('email')

        # For Google login, store email in session
        session['user'] = {'email': email}
        return redirect(url_for('auth.index'))
    except Exception as e:
        return f"Error during login: {str(e)}", 500

@auth_bp.route('/logout')
def logout():
    """
    Logout user and clear session.
    """
    session.pop('user', None)
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
def index():
    """
    Main page of the app.
    """
    if 'user' in session:
        return render_template('index.html')  # Render main app page
    else:
        return redirect(url_for('auth.login'))