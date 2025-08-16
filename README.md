# Intelligent Interview Assistant

<!-- SonarCloud Badges -->
<p>
  <a href="https://sonarcloud.io/summary/overall?id=anindya5"><img src="https://sonarcloud.io/api/project_badges/measure?project=anindya5&metric=alert_status" alt="Quality Gate Status"></a>
  <a href="https://sonarcloud.io/summary/overall?id=anindya5"><img src="https://sonarcloud.io/api/project_badges/measure?project=anindya5&metric=coverage" alt="Coverage"></a>
  <a href="https://sonarcloud.io/summary/overall?id=anindya5"><img src="https://sonarcloud.io/api/project_badges/measure?project=anindya5&metric=bugs" alt="Bugs"></a>
  <a href="https://sonarcloud.io/summary/overall?id=anindya5"><img src="https://sonarcloud.io/api/project_badges/measure?project=anindya5&metric=code_smells" alt="Code Smells"></a>
  <a href="https://sonarcloud.io/summary/overall?id=anindya5"><img src="https://sonarcloud.io/api/project_badges/measure?project=anindya5&metric=sqale_rating" alt="Maintainability"></a>
  <a href="https://sonarcloud.io/summary/overall?id=anindya5"><img src="https://sonarcloud.io/api/project_badges/measure?project=anindya5&metric=security_rating" alt="Security"></a>
</p>

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

## SonarCloud

- CI is configured via `.github/workflows/sonarcloud.yml` to run tests with coverage and publish analysis to SonarCloud.
- Project configuration is in `sonar-project.properties`.
- Ensure you set these values to match your SonarCloud project:
  - `sonar.organization`
  - `sonar.projectKey`

### Enforce status checks on PRs

1. In GitHub, go to Settings → Branches → Add rule (or edit existing for `main`).
2. Enable "Require status checks to pass before merging".
3. Select:
   - "SonarCloud Code Analysis"
   - "SonarCloud Quality Gate"
4. Save. PRs will be blocked until the quality gate passes.
