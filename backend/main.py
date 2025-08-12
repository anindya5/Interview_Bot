from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from typing import List, Dict, Optional
import openai

app = FastAPI()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

class InterviewTopic(BaseModel):
    topic: str
    depth: int = 3  # How many levels deep to go

class InterviewResponse(BaseModel):
    answer: str

interview_context = {}

def generate_followup_questions(topic: str, previous_answers: Dict) -> List[str]:
    """
    Generate follow-up questions based on previous answers
    """
    try:
        # Create a conversation context
        messages = [
            {"role": "system", "content": "You are an expert interviewer. Generate follow-up questions based on the candidate's responses."},
            {"role": "user", "content": f"Topic: {topic}\nPrevious answers: {previous_answers}"}
        ]
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        
        # Extract and format questions
        questions = response.choices[0].message.content.strip().split('\n')
        return [q.strip() for q in questions if q.strip()]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start-interview/")
async def start_interview(topic: InterviewTopic):
    """
    Start a new interview session
    """
    interview_id = os.urandom(16).hex()
    interview_context[interview_id] = {
        "topic": topic.topic,
        "depth": topic.depth,
        "current_depth": 0,
        "questions_asked": [],
        "answers": {}
    }
    return {"interview_id": interview_id}

@app.post("/next-question/")
async def get_next_question(interview_id: str):
    """
    Get the next question in the interview
    """
    if interview_id not in interview_context:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    context = interview_context[interview_id]
    
    if context["current_depth"] >= context["depth"]:
        return {"message": "Interview complete", "summary": generate_summary(context)}
    
    if not context["questions_asked"]:
        # First question
        questions = generate_followup_questions(context["topic"], {})
    else:
        # Generate follow-up based on previous answers
        questions = generate_followup_questions(
            context["topic"], 
            context["answers"]
        )
    
    context["questions_asked"].append(questions[0])
    return {"question": questions[0]}

@app.post("/submit-answer/")
async def submit_answer(interview_id: str, response: InterviewResponse):
    """
    Submit an answer to a question
    """
    if interview_id not in interview_context:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    context = interview_context[interview_id]
    last_question = context["questions_asked"][-1]
    context["answers"][last_question] = response.answer
    context["current_depth"] += 1
    
    return {"message": "Answer received"}

def generate_summary(context: Dict) -> str:
    """
    Generate a summary of the interview
    """
    try:
        messages = [
            {"role": "system", "content": "You are an expert interviewer. Generate a summary of the candidate's responses."},
            {"role": "user", "content": f"Topic: {context['topic']}\nResponses: {context['answers']}"}
        ]
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
