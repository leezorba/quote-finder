from flask import Blueprint, redirect, url_for, session, render_template
from authlib.integrations.flask_client import OAuth
import os

# Create a Flask Blueprint for authentication
auth_bp = Blueprint('auth', __name__)

# Initialize OAuth
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

# Allowed domain for login
ALLOWED_DOMAIN = 'moregoodfoundation.org'

@auth_bp.route('/')
def index():
    """
    Main app page.
    Redirect to login if user is not authenticated.
    """
    if 'user' in session:
        return render_template('index.html')  # Main app page after login
    else:
        return redirect(url_for('auth.login'))


@auth_bp.route('/login')
def login():
    """
    Redirect user to Google login.
    """
    return google.authorize_redirect(url_for('auth.callback', _external=True))


@auth_bp.route('/callback')
def callback():
    """
    Handle Google OAuth callback.
    Validate domain and set session.
    """
    try:
        # Exchange code for token
        google.authorize_access_token()
        user_info = google.get('userinfo').json()
        email = user_info.get('email')

        # Validate email domain
        if email and email.endswith(f"@{ALLOWED_DOMAIN}"):
            session['user'] = user_info
            return redirect(url_for('auth.index'))
        else:
            return "Access denied: unauthorized email domain", 403
    except Exception as e:
        return f"Error during login: {str(e)}", 500


@auth_bp.route('/logout')
def logout():
    """
    Logout user and clear session.
    """
    session.pop('user', None)
    return redirect(url_for('auth.index'))
