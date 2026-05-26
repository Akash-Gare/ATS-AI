from openai import OpenAI
import os
from dotenv import load_dotenv
import re
import json
from datetime import datetime
from db import question_bank_collection

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def generate_interview_questions(student, job):
    # Safe extraction of job mapped fields
    job_title = job.get("jobTitle", job.get("job_title", "General Worker"))
    job_desc = job.get("jobDescription", job.get("description", "No specific description available."))
    job_skills = job.get("requiredSkills", job.get("required_skills", []))
    job_trade = job.get("trade", "")

    # ---------- CACHING LOGIC ----------
    job_id_str = str(job["_id"])
    
    # Check cache hit using job_id
    cached_entry = question_bank_collection.find_one({"job_id": job_id_str})
    if cached_entry:
        print(f"Cache Hit for job_id: {job_id_str}")
        return json.dumps(cached_entry["questions"])
    # ----------------------------------

    prompt = f"""
You are an expert technical interviewer.

Your strict task is to generate exactly 15 Multiple Choice Questions (MCQs) based on short work-related scenarios.
EVERY SINGLE QUESTION (all 15) MUST BE A SHORT SCENARIO. No generic questions, no definitions.

To create these 15 scenario-based MCQs:
1. For each question, invent a TINY scenario (1-2 sentences MAXIMUM) about a problem or situation at work related to the Job Title, Job Description, Required Skills, and Trade.
2. Immediately ask how a candidate would solve it using technical knowledge or required skills.
3. Provide exactly 4 options for each question (Option A, Option B, Option C, Option D).
4. Identify the correct answer (it must match exactly one of the options).

Keep the question text concise!
Example format:
{{
  "question": "Our main database is experiencing high latency during peak hours. How would you use Redis to resolve this bottleneck?",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "Option A"
}}

STRICT RULES:
- Return ONLY a valid JSON array containing exactly 15 questions.
- No explanation.
- No markdown.
- No extra text.
- No ```json blocks.

Job Details:
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

    # ---------- STORE IN CACHE ----------
    try:
        questions_list = json.loads(content)
        question_bank_collection.update_one(
            {"job_id": job_id_str},
            {
                "$set": {
                    "key": job_id_str,  # Compatible with the unique index in db.py
                    "job_id": job_id_str,
                    "questions": questions_list,
                    "trade": job_trade,
                    "skills": job_skills,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        print(f"Cached 15 questions for job_id: {job_id_str}")
    except Exception as e:
        print(f"Failed to cache questions for job_id {job_id_str}: {e}")
    # -----------------------------------

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
