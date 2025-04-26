import os
import secrets
import random
from datetime import datetime, timedelta

from flask import (
    Flask, redirect, session, url_for,
    request, render_template, jsonify
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

# ——— Config —————————————————————————————
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.secret_key = os.getenv("APP_SECRET_KEY") or 'dev_secret_key'

BACKEND_URL   = os.getenv("BACKEND_URL",   "https://auth.bonkmc.org")
DASHBOARD_ID  = os.getenv("DASHBOARD_ID")
DASHBOARD_ACCESS_CODE = os.getenv("DASHBOARD_ACCESS_CODE")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10000 per day"],
    storage_uri="memory://"
)

# ——— Auth Guard ——————————————————————————
@app.before_request
def require_login():
    # allow static & SSO endpoints
    allowed = ('static', 'login_redirect', 'auth_callback')
    if request.endpoint in allowed:
        return
    if 'user' not in session:
        return redirect(url_for('login_redirect'))

# ——— SSO Handlers ————————————————————————
@app.route('/login_redirect')
def login_redirect():
    # send user to backend /login with our server‐config creds
    callback = url_for('auth_callback', _external=True)
    return redirect(
        f"{BACKEND_URL}/login"
        f"?next={callback}"
        f"&server_id={DASHBOARD_ID}"
        f"&secret={DASHBOARD_ACCESS_CODE}"
    )

@app.route('/auth_callback')
def auth_callback():
    # backend returns here as ?username=…
    username = request.args.get('username')
    if not username:
        return "Authentication failed", 401

    session['user'] = username
    # initialize API key if missing
    if 'api_key' not in session:
        session['api_key'] = secrets.token_urlsafe(32)

    return redirect(url_for('dashboard'))

# ——— Pages —————————————————————————————
@app.route('/')
def dashboard():
    return render_template(
        'dashboard.html',
        active='dashboard',
        user=session['user'],
        api_key=session['api_key']
    )

@app.route('/analytics')
def analytics():
    percent_using = 37
    number_using = 278
    percent_quota = 12
    return render_template(
        'analytics.html',
        active='analytics',
        user=session['user'],
        percent_using=percent_using,
        number_using=number_using,
        percent_quota=percent_quota
    )

@app.route('/settings')
def settings():
    return render_template(
        'settings.html',
        active='settings',
        user=session['user'],
        api_key=session['api_key']
    )

# ——— Dashboard API ——————————————————————
@app.route('/api/data')
@limiter.limit("200 per hour")
def get_data():
    labels, values = [], []
    for i in range(6, -1, -1):
        dt = datetime.utcnow() - timedelta(days=i)
        labels.append(dt.strftime("%b %d"))
        values.append(random.randint(10, 100))
    return jsonify({'labels': labels, 'values': values})

@app.route('/api/reset_key', methods=['POST'])
@limiter.limit("50 per hour")
def reset_key():
    new_key = secrets.token_urlsafe(32)
    session['api_key'] = new_key
    return jsonify({
      'status': 'success',
      'message': 'API key updated.',
      'api_key': new_key
    })

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
