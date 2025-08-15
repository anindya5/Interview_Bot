# Intelligent Interview Assistant

An AI-powered interview system that conducts interviews on specific topics and adapts its questions based on candidate responses.

## Features

- Topic-specific interview questions
- Adaptive questioning based on candidate responses
- Real-time interaction
- Natural language processing for responses
- Structured interview flow

## Current AI Model/Tool

- Uses Google Gemini for question generation and scoring logic.
- Configure via `GEMINI_API_KEY` in your environment.

## Tech Stack

- Backend: Flask (`app.py`, `routes.py`)
- Frontend: Vanilla JS + HTML/CSS (`templates/index.html`, `static/js/main.js`, `static/css/style.css`)
- Data: SQLite (`instance/interviews.db`)
- Caching/State: Redis for sessions and onboarding state (see `check_redis.py`, `docker-compose.yml`)

## Onboarding Email Verification

- Endpoints: `/onboarding/start`, `/onboarding/continue`, `/onboarding/resend`
- UX: Inline "Code sent… Expires in mm:ss" banner + "Resend code" button with 60s cooldown
- Limits: Code expiry (~3 minutes), resend cooldown (60s), and attempt limits (enforced server-side)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file with:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

3. Ensure Redis is running (for onboarding/session state):
```bash
# Option A: Docker (if provided in docker-compose)
docker compose up -d redis
# Option B: Local service (macOS example)
brew install redis && brew services start redis
# Verify
python check_redis.py
```

4. Run the application:
```bash
python app.py
```

## Usage

1. Select a topic for the interview
2. Start the interview
3. Respond to questions
4. The system will adapt its questions based on your responses
