from openai import OpenAI
import os
from dotenv import load_dotenv
import re

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def generate_interview_questions(student, job):
    # Safe extraction of nested student skills and trades
    student_skills = []
    for e in student.get("education", []):
        student_skills.extend(e.get("skills", []))
    if not student_skills:
        student_skills = [e.get("trade", "") for e in student.get("education", [])]
    
    student_trades = [e.get("trade", "") for e in student.get("education", []) if e.get("trade")]
    total_exp_roles = len(student.get("experience", []))
    
    # Safe extraction of job mapped fields
    job_title = job.get("jobTitle", job.get("job_title", "General Worker"))
    job_desc = job.get("jobDescription", job.get("description", "No specific description available."))
    job_skills = job.get("requiredSkills", job.get("required_skills", []))
    job_trade = job.get("trade", "")

    prompt = f"""
You are an expert technical interviewer.

Your strict task is to generate exactly 5 very short, concise, scenario-based questions with ideal answers.
EVERY SINGLE QUESTION (all 5) MUST BE A SHORT SCENARIO. No generic questions, no definitions. 

To create these 5 short scenario questions:
1. Cross-reference the "Student's Skills" with the "Job's Required Skills" to find overlapping/matching skills.
2. For each question, invent a TINY scenario (1-2 sentences MAXIMUM, strictly under 40 words total) about a problem at work related to the "Job Title" and "Job Description".
3. Immediately ask how the candidate would use their matching skill to solve it.

Keep the question text extremely short! 
Example "question" format:
"Our main database is experiencing high latency during peak hours. How would you use Redis to resolve this bottleneck?"

ALL 5 QUESTIONS MUST be tiny, 1-2 sentence scenarios.

STRICT RULES:
- Return ONLY valid JSON.
- No explanation.
- No markdown.
- No extra text.
- No ```json blocks.

Format:

[
  {{
    "question": "...",
    "ideal_answer": "..."
  }}
]

Student:
Trade: {', '.join(student_trades)}
Skills: {', '.join(student_skills)}
Experience: {total_exp_roles} roles

Job:
Title: {job_title}
Trade: {job_trade}
Description: {job_desc}
Required Skills: {', '.join(job_skills) if isinstance(job_skills, list) else job_skills}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    content = response.choices[0].message.content.strip()

    # Safety cleanup: extract JSON array
    match = re.search(r'\[.*\]', content, re.DOTALL)
    if match:
        content = match.group(0)
    else:
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

    return content

def evaluate_answer(question, ideal_answer, user_answer):
    prompt = f"""You are a technical interview evaluator.

Question:
{question}

Ideal Answer:
{ideal_answer}

Student Answer:
{user_answer}

Evaluate the student's answer based on:
1. correctness
2. completeness
3. technical accuracy

Give a score from 0 to 10.
Return only the score
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    content = response.choices[0].message.content.strip()

    match = re.search(r'\b(10(?:\.0+)?|\d(?:\.\d+)?)\b', content)
    if match:
        score = float(match.group(1)) * 10.0 # scale from 0-10 to 0-100
    else:
        score = 0.0

    return score
