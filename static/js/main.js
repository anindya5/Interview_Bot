document.addEventListener('DOMContentLoaded', () => {
    const interviewSetup = document.getElementById('interviewSetup');
    const interviewSession = document.getElementById('interviewSession');
    const chatWindow = document.getElementById('chatMessages');
    const answerInput = document.getElementById('responseInput');
    const sendButton = document.getElementById('sendResponse');
    const loader = document.getElementById('loader');

    let sessionId = null; // interview session id
    let onboardingSessionId = null; // onboarding session id
    let isOnboarding = true;
    let candidate = null; // {name, email, phone, topic}

    // Hide setup form if exists and show chat
    if (interviewSetup) interviewSetup.style.display = 'none';
    if (interviewSession) interviewSession.style.display = 'block';

    sendButton.addEventListener('click', handleSend);
    answerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleSend();
        }
    });

    // Kick off onboarding on load
    startOnboarding();

    async function startOnboarding() {
        showLoading(true);
        try {
            const res = await fetch('/onboarding/start', { method: 'POST' });
            const data = await res.json();
            if (data.error) {
                appendMessage('bot', `Error: ${data.error}`);
                return;
            }
            onboardingSessionId = data.onboarding_session_id;
            isOnboarding = true;
            appendMessage('bot', data.message);
            answerInput.placeholder = 'Type here...';
            answerInput.focus();
        } catch (e) {
            appendMessage('bot', 'Failed to start. Please refresh and try again.');
        } finally {
            showLoading(false);
        }
    }

    async function handleSend() {
        const text = answerInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        answerInput.value = '';
        showLoading(true);

        try {
            if (isOnboarding) {
                await continueOnboarding(text);
            } else {
                await submitInterviewAnswer(text);
            }
        } finally {
            showLoading(false);
        }
    }

    async function continueOnboarding(message) {
        if (!onboardingSessionId) return;
        const res = await fetch('/onboarding/continue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ onboarding_session_id: onboardingSessionId, message })
        });
        const data = await res.json();
        if (data.error) {
            appendMessage('bot', `Error: ${data.error}`);
            return;
        }
        if (data.message) appendMessage('bot', data.message);
        if (data.finished) {
            candidate = data.candidate || null;
            isOnboarding = false;
            if (!candidate || !candidate.topic || !candidate.name || !candidate.email) {
                appendMessage('bot', 'Missing info to start interview. Please refresh.');
                return;
            }
            await startInterview(candidate);
        }
    }

    async function startInterview({ topic, name, email }) {
        showLoading(true);
        try {
            const response = await fetch('/start-interview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, name, email })
            });
            const data = await response.json();
            if (data.error) {
                appendMessage('bot', `Error: ${data.error}`);
                return;
            }
            sessionId = data.session_id;
            appendMessage('bot', `Let's begin. The topic is: <strong>${topic}</strong>`);
            appendMessage('bot', data.question);
            answerInput.focus();
        } catch (error) {
            appendMessage('bot', 'An error occurred. Please try again.');
        } finally {
            showLoading(false);
        }
    }

    async function submitInterviewAnswer(answer) {
        if (!sessionId) return;
        const response = await fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, answer })
        });
        const data = await response.json();
        if (data.question) {
            appendMessage('bot', data.question);
        } else if (data.error) {
            appendMessage('bot', `Error: ${data.error}`);
        }
        if (data.finished) {
            answerInput.disabled = true;
            sendButton.disabled = true;
            answerInput.placeholder = 'Interview complete.';
        }
    }

    function appendMessage(sender, text) {
        const messageElement = document.createElement('div');
        const senderClass = sender === 'bot' ? 'question' : 'response';
        messageElement.classList.add('message', senderClass);
        messageElement.innerHTML = text;
        chatWindow.appendChild(messageElement);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function showLoading(isLoading) {
        if (isLoading) {
            loader.style.display = 'flex';
            answerInput.disabled = true;
            sendButton.disabled = true;
        } else {
            loader.style.display = 'none';
            answerInput.disabled = false;
            sendButton.disabled = false;
            answerInput.focus();
        }
    }
});
