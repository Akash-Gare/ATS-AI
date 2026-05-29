from openai import OpenAI
import os
from dotenv import load_dotenv
import re
import json
from datetime import datetime
from db import question_bank_collection, interviews_collection

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def generate_interview_questions(student, job):
    # Extract job details
    job_title = job.get("jobTitle", job.get("job_title", "General Worker"))
    job_desc = job.get("jobDescription", job.get("description", "No specific description available."))
    job_skills = job.get("requiredSkills", job.get("required_skills", []))
    job_trade = job.get("trade", "")

    # Use job_id string as cache key
    job_id_str = str(job["_id"])

    # Check if MCQ bank already exists in interviews collection
    cached = interviews_collection.find_one({"type": "job_mcq_bank", "job_id": job_id_str})
    if cached:
        print(f"Cache Hit for MCQ bank job_id: {job_id_str}")
        return json.dumps(cached["questions"])

    # Build prompt for LLM to generate 15 MCQs
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

    # Extract JSON array
    match = re.search(r'\[.*\]', content, re.DOTALL)
    if match:
        content = match.group(0)
    else:
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

    # ---------- STORE MCQ BANK IN INTERVIEWS ----------
    try:
        questions_list = json.loads(content)
        interviews_collection.insert_one({
            "type": "job_mcq_bank",
            "job_id": job_id_str,
            "questions": questions_list,
            "created_at": datetime.utcnow()
        })
        print(f"Inserted MCQ bank for job_id: {job_id_str}")
    except Exception as e:
        print(f"Failed to store MCQ bank for job_id {job_id_str}: {e}")
    # -----------------------------------

    return content

# NOTE: `evaluate_answer` was removed because the project no longer uses LLM‑based free‑text answer grading.
# MCQ scoring is performed with direct string matching in app.py, so this function was dead code and caused unnecessary token usage.
