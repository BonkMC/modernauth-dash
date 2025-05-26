import os
import secrets
import random
from datetime import datetime, timedelta
from flask import (
    Flask, redirect, session, url_for,
    request, render_template, jsonify, current_app, make_response
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from modernauth.scripts.cli_functions import add_server, remove_server, reset_key as cli_reset_key
from modernauth.app import create_hash
from modernauthdash.db.dashdb import DashboardDB

load_dotenv()

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.secret_key = os.getenv("APP_SECRET_KEY") or 'dev_secret_key'

BACKEND_URL           = os.getenv("BACKEND_URL", "https://auth.bonkmc.org")
DASHBOARD_ID          = os.getenv("DASHBOARD_ID")
DASHBOARD_ACCESS_CODE = os.getenv("DASHBOARD_ACCESS_CODE")

db = DashboardDB(
    mysql_connection=os.getenv("MYSQL"),
    hash_function=create_hash
)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10000 per day"],
    storage_uri="memory://"
)


@app.before_request
def require_login_and_server():
    if request.path.startswith('/api/'):
        return
    if request.endpoint in ('static', 'login_redirect', 'auth_callback'):
        return
    if 'user' not in session:
        return redirect(url_for('login_redirect'))
    if request.endpoint in ('analytics', 'settings'):
        user_data = db.get_user(session['user']) or {}
        if not user_data.get('owned_server'):
            return redirect(url_for('dashboard'))


@app.route('/login_redirect')
def login_redirect():
    callback = url_for('auth_callback', _external=True)
    return redirect(
        f"{BACKEND_URL}/login"
        f"?next={callback}"
        f"&server_id={DASHBOARD_ID}"
        f"&secret={DASHBOARD_ACCESS_CODE}"
    )


@app.route('/auth_callback')
def auth_callback():
    username = request.args.get('username')
    if not username:
        return "Authentication failed", 401
    session['user'] = username
    if 'api_key' not in session:
        session['api_key'] = secrets.token_urlsafe(32)
    db.create_user_if_missing(username)
    return redirect(url_for('dashboard'))


# ←— GET & POST to “/”, routing POST into create_server
@app.route('/', methods=["GET", "POST"])
def dashboard():
    if request.method == 'POST':
        return api_create_server()

    # Pull username from session and coerce if it's a dict
    username = session.get('user')
    if isinstance(username, dict):
        username = username.get('username')
        session['user'] = username
    # Debug log to verify type/value
    print(f"session['user'] type: {type(session['user'])}, value: {session['user']}")

    if not username:
        return redirect(url_for('login_redirect'))
    user_data = db.get_user(username) or {}
    percent_using = 37
    number_using = 278
    percent_quota = 12

    return render_template(
        'dashboard.html',
        active='dashboard',
        user=username,
        user_data=user_data,
        percent_using=percent_using,
        number_using=number_using,
        percent_quota=percent_quota,
        create_server_url=url_for('api_create_server')
    )


@app.route('/api/create_server', methods=['OPTIONS', 'POST'], strict_slashes=False)
def api_create_server():
    if request.method == 'OPTIONS':
        return make_response('', 200)

    username = session.get('user')
    if isinstance(username, dict):
        username = username.get('username')
        session['user'] = username

    if not username:
        return jsonify({'status':'error','message':'Not logged in'}), 401

    data = request.get_json() or {}
    server_id = data.get('server_id','').strip().lower().replace(' ', '-')
    if not server_id:
        return jsonify({'status':'error','message':'Invalid server ID'}), 400

    try:
        secret = add_server(server_id)
    except Exception as e:
        current_app.logger.exception("Error in CLI add_server")
        return jsonify({'status':'error','message': str(e)}), 500

    if not secret:
        return jsonify({'status':'error','message':'Server ID already taken'}), 409

    session['owned_server'] = server_id
    try:
        db.create_user_if_missing(username)
        user_data = db.get_user(username) or {}
        user_data['owned_server'] = server_id
        db.set_user(username, user_data)
    except Exception as e:
        current_app.logger.error("Error updating user_data: %s", e)

    return jsonify({
        'status':'success',
        'owned_server': server_id,
        'secret_key': secret
    }), 200


@app.route('/analytics')
def analytics():
    username = session.get('user')
    if not username:
        return redirect(url_for('login_redirect'))

    user_data = db.get_user(username) or {}
    percent_using = 37
    number_using  = 278
    percent_quota = 12

    return render_template(
        'analytics.html',
        active='analytics',
        user=username,
        user_data=user_data,
        percent_using=percent_using,
        number_using=number_using,
        percent_quota=percent_quota
    )


@app.route('/settings')
def settings():
    username = session.get('user')
    if not username:
        return redirect(url_for('dashboard'))

    user_data = db.get_user(username) or {}
    return render_template(
        'settings.html',
        active='settings',
        user=username,
        user_data=user_data
    )


@app.route('/api/reset_key', methods=['POST'])
def api_reset_key():
    if 'user' not in session:
        return jsonify({'status':'error'}), 401

    new_key = secrets.token_urlsafe(32)
    session['api_key'] = new_key
    return jsonify({'status':'success','api_key':new_key})


@app.route('/api/reset_server_code', methods=['POST'])
def api_reset_server_code():
    username = session.get('user')
    if not username:
        return jsonify({'status':'error','message':'Not logged in'}), 401

    user_data = db.get_user(username) or {}
    server_id = user_data.get('owned_server') or session.get('owned_server')
    if not server_id:
        return jsonify({'status':'error','message':'No server to reset'}), 400

    try:
        new_code = cli_reset_key(server_id)
        return jsonify({'status':'success','new_code':new_code}), 200
    except Exception as e:
        current_app.logger.error("Error resetting server code: %s", e)
        return jsonify({'status':'error','message':'Error resetting server code'}), 500


@app.route('/api/delete_server', methods=['POST'])
def api_delete_server():
    username = session.get('user')
    if not username:
        return jsonify({'status':'error','message':'Not logged in'}), 401

    user_data = db.get_user(username) or {}
    server_id = user_data.get('owned_server') or session.get('owned_server')
    if not server_id:
        return jsonify({'status':'error','message':'No server to delete'}), 400

    try:
        remove_server(server_id)
        session.pop('owned_server', None)
        user_data['owned_server'] = None
        db.set_user(username, user_data)
        return jsonify({'status':'success'}), 200
    except Exception as e:
        current_app.logger.error("Error deleting server: %s", e)
        return jsonify({'status':'error','message':'Error deleting server'}), 500


@app.route('/api/data')
@limiter.limit("200 per hour")
def get_data():
    labels, values = [], []
    for i in range(6, -1, -1):
        dt = datetime.utcnow() - timedelta(days=i)
        labels.append(dt.strftime("%b %d"))
        values.append(random.randint(10, 100))
    return jsonify({'labels': labels, 'values': values})


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host="0.0.0.0")
