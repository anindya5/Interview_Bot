import os
import requests
from .constants import BREVO_SEND_URL


def send_verification_email(to_email: str, code: str):
    brevo_api_key = os.getenv('BREVO_KEY')
    # In non-stage/prod environments, print the code to console to assist local testing
    app_env = (os.getenv('APP_ENV') or os.getenv('FLASK_ENV') or 'local').lower()
    if app_env not in ('stage', 'staging', 'prod', 'production'):
        print(f"[DEV] Verification code for {to_email}: {code}")

    if not brevo_api_key:
        return False, 'BREVO_KEY not configured on server'
    payload = {
        'to': [{ 'email': to_email }],
        'sender': { 'name': 'Interview Assistant', 'email': 'anindya55@gmail.com' },
        'subject': 'Your verification code',
        'htmlContent': f'<p>Your verification code is: <strong>{code}</strong></p>'
    }
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'api-key': brevo_api_key,
    }
    try:
        resp = requests.post(BREVO_SEND_URL, headers=headers, json=payload, timeout=20)
        if 200 <= resp.status_code < 300:
            return True, None
        return False, f'Brevo error {resp.status_code}: {resp.text[:200]}'
    except requests.RequestException as e:
        return False, str(e)
