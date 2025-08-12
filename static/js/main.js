document.addEventListener('DOMContentLoaded', () => {
    const interviewForm = document.getElementById('interviewForm');
    const topicInput = document.getElementById('topic');
    const interviewSetup = document.getElementById('interviewSetup');
    const interviewSession = document.getElementById('interviewSession');
    const chatWindow = document.getElementById('chatMessages');
    const answerInput = document.getElementById('responseInput');
    const sendButton = document.getElementById('sendResponse');
    const loader = document.getElementById('loader');
    let sessionId = null;

    interviewForm.addEventListener('submit', startInterview);

    sendButton.addEventListener('click', sendAnswer);
    answerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendAnswer();
        }
    });

    async function startInterview(e) {
        e.preventDefault(); // Prevent the form from causing a page reload
        const topic = topicInput.value.trim();
        if (!topic) {
            alert('Please enter a topic.');
            return;
        }

        const startButton = interviewForm.querySelector('button');
        startButton.disabled = true;
        loader.style.display = 'flex';
        
        try {
            const response = await fetch('/start-interview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: topic })
            });
            const data = await response.json();

            if (data.error) {
                appendMessage('bot', `Error: ${data.error}`);
            } else {
                sessionId = data.session_id;
                appendMessage('bot', `Let's begin. The topic is: <strong>${topic}</strong>`);
                appendMessage('bot', data.question);
                interviewSetup.style.display = 'none';
                interviewSession.style.display = 'block';
                answerInput.focus();
            }
        } catch (error) {
            appendMessage('bot', 'An error occurred. Please try again.');
        } finally {
            loader.style.display = 'none';
            startButton.disabled = false;
        }
    }

    function sendAnswer() {
        const answer = answerInput.value.trim();
        if (!answer || !sessionId) return;

        appendMessage('user', answer);
        answerInput.value = '';
        showLoading(true);

        fetch('/submit', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ session_id: sessionId, answer: answer })
        })
        .then(response => response.json())
        .then(data => {
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
        })
        .catch(error => {
            console.error('Fetch Error:', error);
            appendMessage('bot', 'An error occurred. Please check the console and try again.');
        })
        .finally(() => {
            showLoading(false);
        });
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
