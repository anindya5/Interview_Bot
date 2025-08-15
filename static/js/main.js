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
    let currentStage = null; // e.g., 'email_code'

    // Resend button and timers
    const chatInputContainer = sendButton.parentElement;
    const resendBtn = document.createElement('button');
    resendBtn.id = 'resendCodeBtn';
    resendBtn.className = 'btn secondary';
    resendBtn.style.marginLeft = '8px';
    resendBtn.style.display = 'none';
    resendBtn.disabled = true;
    resendBtn.textContent = 'Resend code';
    chatInputContainer.appendChild(resendBtn);

    // Inline verification info (expires countdown)
    const verificationInfo = document.createElement('div');
    verificationInfo.id = 'verificationInfo';
    verificationInfo.style.marginLeft = '8px';
    verificationInfo.style.fontSize = '0.9em';
    verificationInfo.style.color = '#666';
    verificationInfo.style.display = 'none';
    chatInputContainer.appendChild(verificationInfo);

    let resendInterval = null;
    let resendRemaining = 0;
    let expiryInterval = null;
    let expiryRemaining = 0;

    function startResendCountdown(seconds) {
        clearInterval(resendInterval);
        resendRemaining = seconds || 60;
        if (resendRemaining <= 0) {
            enableResend();
            return;
        }
        disableResend(`Resend in ${resendRemaining}s`);
        resendInterval = setInterval(() => {
            resendRemaining -= 1;
            if (resendRemaining <= 0) {
                clearInterval(resendInterval);
                enableResend();
            } else {
                disableResend(`Resend in ${resendRemaining}s`);
            }
        }, 1000);
    }

    function startExpiryCountdown(seconds, labelText) {
        clearInterval(expiryInterval);
        expiryRemaining = Math.max(0, seconds || 0);
        if (expiryRemaining <= 0) {
            showVerificationInfo(`${labelText || 'Code sent to your email.'} Expired.`);
            return;
        }
        showVerificationInfo(`${labelText || 'Code sent to your email.'} Expires in ${formatMMSS(expiryRemaining)}.`);
        expiryInterval = setInterval(() => {
            expiryRemaining -= 1;
            if (expiryRemaining <= 0) {
                clearInterval(expiryInterval);
                showVerificationInfo(`${labelText || 'Code sent to your email.'} Expired.`);
            } else {
                showVerificationInfo(`${labelText || 'Code sent to your email.'} Expires in ${formatMMSS(expiryRemaining)}.`);
            }
        }, 1000);
    }

    function formatMMSS(totalSeconds) {
        const m = Math.floor(totalSeconds / 60);
        const s = totalSeconds % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    function enableResend() {
        resendBtn.disabled = false;
        resendBtn.textContent = 'Resend code';
    }
    function disableResend(text) {
        resendBtn.disabled = true;
        resendBtn.textContent = text || 'Resend code';
    }
    function hideResend() {
        resendBtn.style.display = 'none';
        clearInterval(resendInterval);
    }
    function showResend() {
        resendBtn.style.display = 'inline-block';
    }

    function showVerificationInfo(text) {
        verificationInfo.textContent = text;
        verificationInfo.style.display = 'inline-block';
    }
    function hideVerificationInfo() {
        verificationInfo.style.display = 'none';
        verificationInfo.textContent = '';
        clearInterval(expiryInterval);
    }

    resendBtn.addEventListener('click', async () => {
        if (!onboardingSessionId) return;
        showLoading(true);
        try {
            const res = await fetch('/onboarding/resend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ onboarding_session_id: onboardingSessionId })
            });
            const data = await res.json();
            if (data.error) {
                appendMessage('bot', `Error: ${data.error}`);
                return;
            }
            if (data.message) appendMessage('bot', data.message);
            // Update meta and cooldown
            if (typeof data.resend_available_in === 'number') {
                showResend();
                startResendCountdown(data.resend_available_in);
            }
            if (typeof data.expires_in === 'number') {
                startExpiryCountdown(data.expires_in, 'Code resent to your email.');
            }
            // If backend signals finished/end for any reason
            if (data.finished) {
                isOnboarding = false;
                hideResend();
                hideVerificationInfo();
            }
        } catch (e) {
            appendMessage('bot', 'Failed to resend code. Please try again shortly.');
        } finally {
            showLoading(false);
        }
    });

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

    function handleVerificationMeta(data) {
        currentStage = data.stage || null;
        if (currentStage === 'email_code') {
            showResend();
            if (typeof data.resend_available_in === 'number') {
                startResendCountdown(data.resend_available_in);
            }
            if (typeof data.expires_in === 'number') {
                startExpiryCountdown(data.expires_in, 'Code sent to your email.');
            }
            // Optionally display attempts/expires info in chat stream
            if (typeof data.attempts_left === 'number' && typeof data.expires_in === 'number') {
                appendMessage('bot', `You have ${data.attempts_left} attempt(s) left. Code expires in ${data.expires_in}s.`);
            }
        } else {
            hideResend();
            hideVerificationInfo();
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
        if (data.stage) {
            handleVerificationMeta(data);
        }
        if (data.message) appendMessage('bot', data.message);
        if (data.finished) {
            hideResend();
            hideVerificationInfo();
            if (data.candidate) {
                candidate = data.candidate;
                isOnboarding = false;
                if (!candidate.topic || !candidate.name || !candidate.email) {
                    appendMessage('bot', 'Missing info to start interview. Please refresh.');
                    return;
                }
                await startInterview(candidate);
            } else {
                // Onboarding ended without candidate (e.g., timeout/too many attempts)
                answerInput.disabled = true;
                sendButton.disabled = true;
            }
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
            resendBtn.disabled = true;
        } else {
            loader.style.display = 'none';
            answerInput.disabled = false;
            sendButton.disabled = false;
            // resend button state controlled separately by countdown
            answerInput.focus();
        }
    }
});
