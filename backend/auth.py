import os
import jwt
import requests
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Blueprint, request, jsonify, redirect

auth_bp = Blueprint('auth', __name__)

GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
JWT_SECRET = os.getenv('JWT_SECRET_KEY')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
JWT_EXPIRY_HOURS = 24


def _create_jwt(user_data):
    payload = {
        'sub': str(user_data['id']),
        'login': user_data['login'],
        'name': user_data.get('name', ''),
        'avatar_url': user_data.get('avatar_url', ''),
        'github_token': user_data['github_token'],
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def require_auth(f):
    """Decorator that enforces JWT authentication on a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif request.headers.get('X-Docrot-Token'):
            token = request.headers.get('X-Docrot-Token')

        if not token:
            return jsonify({'error': 'Missing authentication token'}), 401

        try:
            request.user = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/api/auth/login')
def login():
    if not GITHUB_CLIENT_ID:
        return jsonify({'error': 'GitHub OAuth not configured'}), 500
    github_auth_url = (
        'https://github.com/login/oauth/authorize'
        f'?client_id={GITHUB_CLIENT_ID}'
        '&scope=read:user,repo'
    )
    return redirect(github_auth_url)


@auth_bp.route('/api/auth/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(f'{FRONTEND_URL}?error=missing_code')

    token_response = requests.post(
        'https://github.com/login/oauth/access_token',
        headers={'Accept': 'application/json'},
        json={
            'client_id': GITHUB_CLIENT_ID,
            'client_secret': GITHUB_CLIENT_SECRET,
            'code': code,
        },
        timeout=10,
    )

    token_data = token_response.json()
    github_token = token_data.get('access_token')
    if not github_token:
        return redirect(f'{FRONTEND_URL}?error=token_exchange_failed')

    user_response = requests.get(
        'https://api.github.com/user',
        headers={
            'Authorization': f'Bearer {github_token}',
            'Accept': 'application/vnd.github+json',
        },
        timeout=10,
    )

    if user_response.status_code != 200:
        return redirect(f'{FRONTEND_URL}?error=user_fetch_failed')

    user_data = user_response.json()
    user_data['github_token'] = github_token
    jwt_token = _create_jwt(user_data)

    return redirect(f'{FRONTEND_URL}?token={jwt_token}')


@auth_bp.route('/api/auth/me')
@require_auth
def me():
    return jsonify({
        'login': request.user['login'],
        'name': request.user.get('name'),
        'avatar_url': request.user.get('avatar_url'),
    })
