import os
import uuid
import json
import random
import time
import requests
from dataclasses import dataclass, asdict
from typing import Optional

BREVO_SEND_URL = 'https://api.brevo.com/v3/smtp/email'


@dataclass
class OnboardingState:
    session_id: str
    step: str  # welcome, name, email, email_code, phone, topic, done
    name: str = ''
    email: str = ''
    phone: str = ''
    topic: str = ''
    email_code: str = ''  # generated 5-digit code
    created_at: float = 0.0

    def to_dict(self):
        d = asdict(self)
        return {k: ('' if v is None else (json.dumps(v) if isinstance(v, (dict, list)) else str(v))) for k, v in d.items()}

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            session_id=d.get('session_id', ''),
            step=d.get('step', 'welcome'),
            name=d.get('name', ''),
            email=d.get('email', ''),
            phone=d.get('phone', ''),
            topic=d.get('topic', ''),
            email_code=d.get('email_code', ''),
            created_at=float(d.get('created_at', '0') or 0.0),
        )


class OnboardingSession:
    def __init__(self, r, session_id: Optional[str] = None):
        self.r = r
        self.session_id = session_id or str(uuid.uuid4())
        self.state: Optional[OnboardingState] = None

    @property
    def redis_key(self):
        return f"onboarding:{self.session_id}"

    def save(self):
        if not self.r:
            return
        self.r.hset(self.redis_key, mapping=self.state.to_dict())

    @classmethod
    def load(cls, r, session_id: str):
        data = r.hgetall(f"onboarding:{session_id}") if r else None
        if not data:
            return None
        sess = cls(r, session_id=session_id)
        sess.state = OnboardingState.from_dict(data)
        return sess

    def start(self):
        # Initialize state and return welcome prompt
        self.state = OnboardingState(
            session_id=self.session_id,
            step='name',
            created_at=time.time(),
        )
        self.save()
        return {
            'session_id': self.session_id,
            'message': "Welcome to the Intelligent Interview Assistant! Let's get you set up. What's your full name?",
            'finished': False,
        }

    def continue_flow(self, user_message: str):
        if not self.state:
            return {'error': 'Onboarding session not found.', 'finished': True}

        step = self.state.step

        if step == 'name':
            name = user_message.strip()
            if len(name) < 2:
                return {'message': 'Please provide your full name.'}
            self.state.name = name
            self.state.step = 'email'
            self.save()
            return {'message': f'Thanks, {name}. What is your email address?'}

        if step == 'email':
            email = user_message.strip()
            if not self._looks_like_email(email):
                return {'message': 'That does not look like a valid email. Please re-enter your email address.'}
            self.state.email = email
            # Generate and send verification code
            code = f"{random.randint(10000, 99999)}"
            self.state.email_code = code
            send_ok, err = self._send_email_code(email, code)
            self.state.step = 'email_code'
            self.save()
            if not send_ok:
                return {'message': f'Could not send verification email: {err}. Please enter the 5-digit code if you received it, or type RESEND to try again.'}
            return {'message': f"I've sent a 5-digit verification code to {email}. Please enter the code here. Please also check your spam folderType RESEND to send it again."}

        if step == 'email_code':
            code_input = user_message.strip()
            if code_input.upper() == 'RESEND':
                code = f"{random.randint(10000, 99999)}"
                self.state.email_code = code
                send_ok, err = self._send_email_code(self.state.email, code)
                self.save()
                if not send_ok:
                    return {'message': f'Failed to resend email: {err}. You can try again with RESEND or enter the code if received.'}
                return {'message': 'A new code has been sent. Please enter the 5-digit code.'}
            if code_input == self.state.email_code:
                self.state.step = 'phone'
                self.save()
                return {'message': 'Email verified! What is your phone number? (digits only, include country code if outside US)'}
            return {'message': 'Incorrect code. Please try again or type RESEND.'}

        if step == 'phone':
            phone = user_message.strip()
            digits = ''.join(ch for ch in phone if ch.isdigit())
            if len(digits) < 7:
                return {'message': 'Please enter a valid phone number (at least 7 digits).'}
            self.state.phone = digits
            self.state.step = 'topic'
            self.save()
            return {'message': 'Great. What topic are you interviewing for?'}

        if step == 'topic':
            topic = user_message.strip()
            if len(topic) < 2:
                return {'message': 'Please provide a valid topic.'}
            self.state.topic = topic
            self.state.step = 'done'
            self.save()
            # Final payload to start interview client-side
            return {
                'message': f"Thanks! You're all set for the {topic} interview.",
                'finished': True,
                'candidate': {
                    'name': self.state.name,
                    'email': self.state.email,
                    'phone': self.state.phone,
                    'topic': self.state.topic,
                }
            }

        return {'error': 'Invalid onboarding step.', 'finished': True}

    def _looks_like_email(self, email: str) -> bool:
        return '@' in email and '.' in email and len(email) >= 6

    def _send_email_code(self, to_email: str, code: str):
        brevo_api_key = os.getenv('BREVO_KEY')
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
            if resp.status_code >= 200 and resp.status_code < 300:
                return True, None
            return False, f'Brevo error {resp.status_code}: {resp.text[:200]}'
        except requests.RequestException as e:
            return False, str(e)
