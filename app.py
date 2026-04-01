from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from services.llm_service import generate_interview_questions, evaluate_answer
from fastapi import HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
import os
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
from datetime import datetime, timedelta
from db import students_collection, jobs_collection, interviews_collection, applications_collection

# Configure SMTP
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

from services.scoring_service import calculate_skills_similarity, calculate_job_match

app = FastAPI(title="ATS AI Engine")

# Serve frontend
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")

# Ensure upload folders exist
os.makedirs("uploads/profile_pics", exist_ok=True)
os.makedirs("uploads/resumes", exist_ok=True)

# Serve uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ---------- Models ----------

class Education(BaseModel):
    educationType: str
    boardName: str
    trade: str
    skills: List[str] = []
    instituteName: str
    passingYear: int

class Experience(BaseModel):
    companyName: str
    jobTitle: str
    isCurrentlyWorking: bool = False
    employmentType: str = "Full time"
    jobDescription: str

class Preferences(BaseModel):
    expectedSalary: str = ""
    preferredLocations: str = ""

class Student(BaseModel):
    userId: str
    fullName: str
    email: str = ""
    password: str = ""
    mobile: str = ""
    dob: str = ""
    city: str
    state: str
    education: List[Education] = []
    experience: List[Experience] = []
    preferences: Optional[Preferences] = None
    isProfileComplete: bool = False


class Address(BaseModel):
    city: str = ""
    state: str = ""
    pincode: str = ""

class Salary(BaseModel):
    min: int = 0
    max: int = 0

class Job(BaseModel):
    company: str = ""
    employerId: str = ""
    jobTitle: str = ""
    trade: str = ""
    jobType: str = ""
    experienceLevel: str = ""
    address: dict = {} 
    locations: list = []
    location: str = ""
    salary: dict = {}
    numberOfVacancies: int = 1
    jobDescription: str = ""
    responsibilities: List[str] = []
    requiredSkills: List[str] = []
    preferredSkills: List[str] = []
    educationLevel: str = ""
    certifications: List[str] = []
    experienceRequirements: str = ""
    min_experience: int = 0
    benefits: List[str] = []
    additionalInfo: str = ""
    status: str = "active"
    totalApplicants: int = 0

#--------Login--------#

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/students/login")
def student_login(data: LoginRequest):
    student = students_collection.find_one({
        "email": data.email,
        "password": data.password
    })

    if not student:
        return {"success": False, "message": "Invalid credentials"}

    return {
        "success": True,
        "student_id": str(student["_id"])
    }


# ---------- Health ----------

@app.get("/health")
def health():
    return {"status": "ATS AI running"}

@app.get("/system/sync_chroma")
def sync_chromadb():
    """Fetches all past jobs from MongoDB and stores their embeddings into ChromaDB"""
    from db import jobs_vector_collection, jobs_collection
    
    if not jobs_vector_collection:
        return {"error": "ChromaDB is disabled. You cannot sync."}
        
    jobs = list(jobs_collection.find())
    count = 0
    
    for job in jobs:
        job_id = str(job["_id"])
        skills_str = ", ".join(job.get('requiredSkills', []))
        job_text = f"Job Title: {job.get('jobTitle', '')}\nTrade: {job.get('trade', '')}\nSkills: {skills_str}\nDescription: {job.get('jobDescription', '')}"
        
        try:
            jobs_vector_collection.upsert(
                documents=[job_text],
                ids=[job_id],
                metadatas=[{
                    "job_title": job.get("jobTitle", ""),
                    "trade": job.get("trade", ""),
                    "experience_level": job.get("experienceLevel", "Fresher"),
                    "location": job.get("address", {}).get("city", "")
                }]
            )
            count += 1
        except Exception as e:
            print(f"Failed to sync job {job_id}: {e}")
            
    return {"message": "Success", "jobs_embedded_in_chromadb": count}


# ---------- APIs ----------

@app.post("/students/register")
def register_student(student: Student):
    result = students_collection.insert_one(student.dict())
    return {
        "message": "Student registered successfully",
        "student_id": str(result.inserted_id)
    }


@app.get("/students/{student_id}")
def get_student(student_id: str):
    if not ObjectId.is_valid(student_id):
        return {"error": "Invalid student id"}

    student = students_collection.find_one(
        {"_id": ObjectId(student_id)}
    )

    if not student:
        return {"error": "Student not found"}

    student["_id"] = str(student["_id"])
    return student


class StudentUpdate(BaseModel):
    fullName: str
    dob: str = ""
    mobile: str = ""
    email: str = ""
    city: str = ""
    state: str = ""

class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

def send_otp_email(recipient_email, otp):
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    current_smtp_email = os.getenv("SMTP_EMAIL", "").strip()
    current_smtp_password = os.getenv("SMTP_PASSWORD", "").strip()

    if not current_smtp_email or not current_smtp_password or current_smtp_email == "your_email_here@gmail.com":
        print(f"MOCK EMAIL (SMTP not properly configured): To {recipient_email}, Your OTP is {otp}")
        return True
        
    try:
        msg = MIMEMultipart()
        msg['From'] = current_smtp_email
        msg['To'] = recipient_email
        msg['Subject'] = "ATS Connect - Password Reset OTP"
        
        body = f"Hello,\n\nYou requested to reset your password. Use the following OTP to proceed:\n\n{otp}\n\nThis OTP is valid for 10 minutes.\nIf you did not request this, please ignore this email.\n\nRegards,\nATS Connect Team"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(current_smtp_email, current_smtp_password)
        text = msg.as_string()
        server.sendmail(current_smtp_email, recipient_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Flow failed: {e}")
        return False


@app.post("/students/forgot-password/send-otp")
def forgot_password_send_otp(req: ForgotPasswordRequest):
    student = students_collection.find_one({"email": req.email})
    if not student:
        return {"success": False, "message": "Email not found"}
        
    otp = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=10)
    
    students_collection.update_one(
        {"_id": student["_id"]},
        {"$set": {"reset_otp": otp, "reset_otp_expiry": expiry}}
    )
    
    email_sent = send_otp_email(req.email, otp)
    
    if email_sent:
        return {"success": True, "message": "OTP sent successfully"}
    else:
        return {"success": False, "message": "Failed to send OTP email"}

@app.post("/students/forgot-password/verify-otp")
def forgot_password_verify_otp(req: VerifyOTPRequest):
    student = students_collection.find_one({"email": req.email})
    if not student:
        return {"success": False, "message": "Invalid email"}
        
    stored_otp = student.get("reset_otp")
    expiry = student.get("reset_otp_expiry")
    
    if not stored_otp or stored_otp != req.otp:
        return {"success": False, "message": "Invalid OTP"}
        
    if not expiry or datetime.utcnow() > expiry:
        return {"success": False, "message": "OTP has expired"}
        
    return {"success": True, "message": "OTP verified successfully"}

@app.post("/students/forgot-password/reset")
def forgot_password_reset(req: ResetPasswordRequest):
    student = students_collection.find_one({"email": req.email})
    if not student:
        return {"success": False, "message": "Invalid email"}
        
    stored_otp = student.get("reset_otp")
    expiry = student.get("reset_otp_expiry")
    
    if not stored_otp or stored_otp != req.otp:
        return {"success": False, "message": "Invalid OTP"}
        
    if not expiry or datetime.utcnow() > expiry:
        return {"success": False, "message": "OTP has expired"}
        
    students_collection.update_one(
        {"_id": student["_id"]},
        {
            "$set": {"password": req.new_password},
            "$unset": {"reset_otp": "", "reset_otp_expiry": ""}
        }
    )
    return {"success": True, "message": "Password reset successfully"}


@app.put("/students/update/{student_id}")
def update_student(student_id: str, data: StudentUpdate):
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student id")
    
    result = students_collection.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {
            "fullName": data.fullName,
            "dob": data.dob,
            "mobile": data.mobile,
            "email": data.email,
            "city": data.city,
            "state": data.state
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": "Profile updated successfully"}


@app.post("/students/{student_id}/upload")
def upload_files(
    student_id: str,
    profilePic: Optional[UploadFile] = File(None),
    resume: Optional[UploadFile] = File(None)
):
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student id")
    
    update_data = {}
    
    if profilePic:
        pic_filename = f"{student_id}_{profilePic.filename}"
        pic_path = os.path.join("uploads", "profile_pics", pic_filename)
        with open(pic_path, "wb") as buffer:
            shutil.copyfileobj(profilePic.file, buffer)
        update_data["profilePicUrl"] = f"/uploads/profile_pics/{pic_filename}"
        
    if resume:
        resume_filename = f"{student_id}_{resume.filename}"
        resume_path = os.path.join("uploads", "resumes", resume_filename)
        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(resume.file, buffer)
        update_data["resumeUrl"] = f"/uploads/resumes/{resume_filename}"
        
    if update_data:
        students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": update_data}
        )
        return {"message": "Files uploaded successfully", "data": update_data}
    
    return {"message": "No files provided"}


@app.post("/jobs/post")
def post_job(job: Job):
    from db import jobs_vector_collection
    
    # Store in MongoDB
    result = jobs_collection.insert_one(job.dict())
    job_id = str(result.inserted_id)
    
    # Store in DB (DISABLED)
    if jobs_vector_collection:
        try:
            skills_str = ", ".join(job.requiredSkills)
            job_text = f"Job Title: {job.jobTitle}\nTrade: {job.trade}\nSkills: {skills_str}\nDescription: {job.jobDescription}"
            
            jobs_vector_collection.add(
                documents=[job_text],
                ids=[job_id],
                metadatas=[{
                    "job_title": job.jobTitle,
                    "trade": job.trade,
                    "experience_level": job.experienceLevel,
                    "location": job.location
                }]
            )
        except Exception as e:
            print(f"ChromaDB Error: {e}")
    else:
        print("ChromaDB is disabled. Skipping vector insertion.")

    
    return {
        "message": "Job posted successfully",
        "job_id": job_id
    }


def serialize_mongo(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: serialize_mongo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_mongo(i) for i in obj]
    return obj

@app.get("/jobs")
def get_jobs():
    jobs = list(jobs_collection.find())
    return [serialize_mongo(job) for job in jobs]

@app.post("/jobs/apply/{student_id}/{job_id}")
def apply_job(student_id: str, job_id: str):
    import datetime
    if not ObjectId.is_valid(student_id) or not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    student = students_collection.find_one({"_id": ObjectId(student_id)})
    job = jobs_collection.find_one({"_id": ObjectId(job_id)})

    if not student or not job:
        raise HTTPException(status_code=404, detail="Student or Job not found")

    application = {
        "student_id": student_id,
        "job_id": job_id,
        "application_status": "applied",
        "applied_date": datetime.datetime.now().strftime("%Y-%m-%d")
    }

    result = applications_collection.insert_one(application)

    return {
        "message": "Application submitted successfully",
        "application_id": str(result.inserted_id)
    }

@app.get("/recommend/{student_id}")
def get_recommendations(student_id: str):
    from db import jobs_vector_collection
    if not ObjectId.is_valid(student_id):
        return {"error": "Invalid student id"}

    student = students_collection.find_one(
        {"_id": ObjectId(student_id)}
    )

    if not student:
        return {"error": "Student not found"}

    # Get job stats
    jobs_count = jobs_collection.count_documents({})
    if jobs_count == 0:
        return {"error": "No jobs found"}

    # Convert student profile to text for semantic search
    # Gather all trades and skills from education
    student_trades = [e.get("trade", "") for e in student.get("education", [])]
    student_skills = []
    for e in student.get("education", []):
        student_skills.extend(e.get("skills", []))
    
    # Gather all experience details
    experiences = [f"{exp.get('jobTitle')} at {exp.get('companyName')}: {exp.get('jobDescription')}" for exp in student.get("experience", [])]
    
    student_text = f"Full Name: {student.get('fullName')}\nTrades: {', '.join(student_trades)}\nSkills: {', '.join(student_skills)}\nExperience: {' | '.join(experiences)}"


    # Query DB (Conditional Fallback)
    recommendations = []
    
    if jobs_vector_collection:
        # 1. Fetch a larger pool using semantic search to ensure we don't prematurely filter out exact skill overlaps
        vector_count = jobs_vector_collection.count()
        if vector_count > 0:
            n_results = min(50, vector_count)
            results = jobs_vector_collection.query(
                query_texts=[student_text],
                n_results=n_results
            )
        else:
            results = {"ids": []}
        
        temp_recs = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for idx, job_id in enumerate(results["ids"][0]):
                job = jobs_collection.find_one({"_id": ObjectId(job_id)})
                if job:
                    # 2. Evaluate with Hybrid Skill Matching Approach (Exact + Semantic)
                    final_score = calculate_job_match(student, job)
                    trade = job.get("trade", "")
                    company = job.get("company") or (trade.capitalize() + " Industry" if trade else "Unknown Company")
                    temp_recs.append({
                        "job_id": str(job["_id"]),
                        "job_title": job.get("jobTitle", job.get("job_title", "Untitled")),
                        "company": company,
                        "trade": trade,
                        "score": round(float(final_score), 2)
                    })
            
            # 3. Sort by our Hybrid Match Score and return Top 5
            temp_recs.sort(key=lambda x: x["score"], reverse=True)
            recommendations = temp_recs[:5]
    else:
        # Fallback: Manual skill matching for all jobs
        all_jobs = list(jobs_collection.find())
        temp_recs = []
        for job in all_jobs:
            final_score = calculate_job_match(student, job)
            trade = job.get("trade", "")
            company = job.get("company") or (trade.capitalize() + " Industry" if trade else "Unknown Company")
            temp_recs.append({
                "job_id": str(job["_id"]),
                "job_title": job.get("jobTitle", job.get("job_title", "Untitled")),
                "company": company,
                "trade": trade,
                "score": round(float(final_score), 2)
            })
        
        # Sort and take top 5
        temp_recs.sort(key=lambda x: x["score"], reverse=True)
        recommendations = temp_recs[:5]

    # Sort descending
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return {
        "student": student["fullName"],
        "recommendations": recommendations
    }

@app.post("/interview/start/{student_id}/{job_id}")
def start_interview(student_id: str, job_id: str):

    student = students_collection.find_one({"_id": ObjectId(student_id)})
    job = jobs_collection.find_one({"_id": ObjectId(job_id)})

    if not student or not job:
        raise HTTPException(status_code=404, detail="Student or Job not found")

    # Generate questions from Groq
    llm_output = generate_interview_questions(student, job)

    import json

    try:
        questions = json.loads(llm_output)
    except Exception as e:
        print("LLM RAW OUTPUT:", llm_output)
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")


    interview_data = {
        "student_id": student_id,
        "job_id": job_id,
        "questions": [
            {
                "question": q["question"],
                "ideal_answer": q["ideal_answer"],
                "student_answer": "",
                "score": 0
            }
            for q in questions
        ],
        "interview_score": 0,
        "final_score": 0,
        "feedback": ""
    }

    result = interviews_collection.insert_one(interview_data)

    return {
        "interview_id": str(result.inserted_id),
        "questions": [q["question"] for q in questions]
    }


@app.get("/interview/{interview_id}")
def get_interview(interview_id: str):

    interview = interviews_collection.find_one({"_id": ObjectId(interview_id)})

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return {
        "questions": [q["question"] for q in interview["questions"]]
    }



class Answer(BaseModel):
    question: str
    answer: str

class InterviewSubmission(BaseModel):
    answers: List[Answer]



@app.post("/interview/submit/{interview_id}")
def submit_interview(interview_id: str, submission: InterviewSubmission):

    interview = interviews_collection.find_one({"_id": ObjectId(interview_id)})

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    total_score = 0
    num_questions = len(interview.get("questions", []))

    if num_questions == 0:
        raise HTTPException(status_code=400, detail="No questions found")

    import json

    # 🔹 Per Question Scoring
    for i, ans in enumerate(submission.answers):

        question_text = interview["questions"][i]["question"]
        ideal_answer = interview["questions"][i]["ideal_answer"]
        student_answer = ans.answer.strip()

        # Evaluate using Mixtral LLM
        try:
            from services.llm_service import evaluate_answer
            similarity_score = evaluate_answer(question_text, ideal_answer, student_answer)
            question_feedback = "Good" if similarity_score >= 80 else ("Average" if similarity_score >= 50 else "Needs improvement")
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            similarity_score = 0.0
            question_feedback = "Error evaluating answer."

        interview["questions"][i]["student_answer"] = student_answer
        interview["questions"][i]["score"] = similarity_score
        interview["questions"][i]["feedback"] = question_feedback

        total_score += similarity_score

    # 🔹 Interview Score (Average)
    interview_score = round(total_score / num_questions, 2)

    # 🔹 Fetch Student & Job For Match Score
    student = students_collection.find_one({"_id": ObjectId(interview["student_id"])})
    job = jobs_collection.find_one({"_id": ObjectId(interview["job_id"])})

    job_match_score = calculate_job_match(student, job)

    # 🔹 Weighted Final Score
    final_score = round(
        (0.6 * interview_score) + (0.4 * job_match_score),
        2
    )

    # 🔹 Feedback Logic
    if final_score >= 80:
        feedback = "Strong 💪"
    elif final_score >= 60:
        feedback = "Good 👍"
    elif final_score >= 40:
        feedback = "Average 🙂"
    else:
        feedback = "Weak ⚠"

    # 🔹 Update Database
    interviews_collection.update_one(
        {"_id": ObjectId(interview_id)},
        {
            "$set": {
                "questions": interview["questions"],
                "interview_score": interview_score,
                "job_match_score": job_match_score,
                "final_score": final_score,
                "feedback": feedback
            }
        }
    )

    return {
        "interview_score": interview_score,
        "job_match_score": job_match_score,
        "final_score": final_score,
        "feedback": feedback
    }



@app.get("/interview/result/{interview_id}")
def get_result(interview_id: str):

    interview = interviews_collection.find_one({"_id": ObjectId(interview_id)})

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    return {
        "student_id": str(interview.get("student_id")),
        "interview_score": interview.get("interview_score", 0),
        "job_match_score": interview.get("job_match_score", 0),
        "final_score": interview.get("final_score", 0),
        "feedback": interview.get("feedback", "Pending")
    }
