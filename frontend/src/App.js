import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [interviewId, setInterviewId] = useState('');
  const [topic, setTopic] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [answers, setAnswers] = useState([]);
  const [isInterviewStarted, setIsInterviewStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState('');

  const startInterview = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('http://localhost:8000/start-interview/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic }),
      });
      
      const data = await response.json();
      setInterviewId(data.interview_id);
      setIsInterviewStarted(true);
      getNextQuestion();
    } catch (error) {
      console.error('Error starting interview:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getNextQuestion = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`http://localhost:8000/next-question/?interview_id=${interviewId}`);
      const data = await response.json();
      
      if (data.message === 'Interview complete') {
        setIsInterviewStarted(false);
        setSummary(data.summary);
        return;
      }
      
      setCurrentQuestion(data.question);
    } catch (error) {
      console.error('Error getting next question:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const submitAnswer = async (answer) => {
    try {
      setIsLoading(true);
      const response = await fetch('http://localhost:8000/submit-answer/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ interview_id: interviewId, answer }),
      });
      
      const data = await response.json();
      setAnswers([...answers, answer]);
      getNextQuestion();
    } catch (error) {
      console.error('Error submitting answer:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Smart Interview Assistant</h1>
      </header>
      
      {!isInterviewStarted ? (
        <div className="start-interview-section">
          <input
            type="text"
            placeholder="Enter interview topic..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
          <button onClick={startInterview} disabled={isLoading || !topic}>
            {isLoading ? 'Starting...' : 'Start Interview'}
          </button>
        </div>
      ) : (
        <div className="interview-section">
          <div className="question-container">
            <h2>Current Question:</h2>
            <p>{currentQuestion}</p>
          </div>
          <div className="answer-container">
            <textarea
              placeholder="Type your answer here..."
              onChange={(e) => setAnswers([...answers, e.target.value])}
            />
            <button onClick={() => submitAnswer(answers[answers.length - 1])} disabled={isLoading}>
              {isLoading ? 'Submitting...' : 'Submit Answer'}
            </button>
          </div>
          {summary && (
            <div className="summary-section">
              <h2>Interview Summary:</h2>
              <p>{summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
