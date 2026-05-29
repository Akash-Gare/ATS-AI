from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from services.llm_service import generate_interview_questions
from services.pdf_service import generate_interview_report
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
from db import students_collection, jobs_collection, interviews_collection, applications_collection, interview_questions_collection, interview_results_collection

# Configure SMTP
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

from services.scoring_service import calculate_skills_similarity, calculate_job_match
from services.location_service import get_coordinates_from_pincode

app = FastAPI(title="ATS AI Engine")

# Serve frontend
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")

# Ensure upload folders exist
os.makedirs("uploads/profile_pics", exist_ok=True)
os.makedirs("uploads/resumes", exist_ok=True)
os.makedirs("uploads/reports", exist_ok=True)
os.makedirs("uploads/documents", exist_ok=True)

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
    rollNumber: str = ""
    certificateNumber: str = ""

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
    profilePhoto: str = ""
    pinCode: str = ""
    area: str = ""
    taluka: str = ""
    district: str = ""
    trade: str = ""
    skills: List[str] = []
    instituteId: str = ""
    documents: Optional[dict] = {
        "tenthMarksheet": None,
        "twelfthMarksheet": None,
        "finalSemMarksheet": None,
        "provisionalDegreeCertificate": None,
        "apprenticeCertificate": None,
        "experienceCertificate": None
    }
    savedJobs: List[str] = []
    applicationStatus: str = "Not Applied"
    placementStatus: str = "Not Placed"
    education: List[Education] = []
    experience: List[Experience] = []
    preferences: Optional[Preferences] = None
    isProfileComplete: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Address(BaseModel):
    city: str
    state: str
    pincode: str

class Salary(BaseModel):
    min: int
    max: int

class Job(BaseModel):
    company: str = ""
    employerId: str = ""
    jobTitle: str = ""
    trade: str = ""
    jobType: str = ""
    experienceLevel: str = ""
    address: Address
    locations: List[str] = []
    location: str = ""
    salary: Salary
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
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
    student_dict = student.dict()
    if student.pinCode or student.city or student.state or student.area:
        lat, lon = get_coordinates_from_pincode(student.pinCode, student.city, student.state, student.area)
        student_dict["latitude"] = lat
        student_dict["longitude"] = lon
    result = students_collection.insert_one(student_dict)
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
    area: str = ""
    taluka: str = ""
    district: str = ""
    pinCode: str = ""
    skills: List[str] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
    
    update_fields = {
        "fullName": data.fullName,
        "dob": data.dob,
        "mobile": data.mobile,
        "email": data.email,
        "city": data.city,
        "state": data.state,
        "area": data.area,
        "taluka": data.taluka,
        "district": data.district,
        "pinCode": data.pinCode,
        "skills": data.skills
    }
    
    if data.pinCode or data.city or data.state or data.area:
        lat, lon = get_coordinates_from_pincode(data.pinCode, data.city, data.state, data.area)
        update_fields["latitude"] = lat
        update_fields["longitude"] = lon
        
    result = students_collection.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": "Profile updated successfully"}


@app.post("/students/{student_id}/upload")
def upload_files(
    student_id: str,
    profilePic: Optional[UploadFile] = File(None),
    resume: Optional[UploadFile] = File(None),
    tenthMarksheet: Optional[UploadFile] = File(None),
    twelfthMarksheet: Optional[UploadFile] = File(None),
    finalSemMarksheet: Optional[UploadFile] = File(None),
    provisionalDegreeCertificate: Optional[UploadFile] = File(None),
    apprenticeCertificate: Optional[UploadFile] = File(None),
    experienceCertificate: Optional[UploadFile] = File(None)
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
        update_data["profilePhoto"] = f"/uploads/profile_pics/{pic_filename}"
        
    if resume:
        resume_filename = f"{student_id}_{resume.filename}"
        resume_path = os.path.join("uploads", "resumes", resume_filename)
        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(resume.file, buffer)
        update_data["resumeUrl"] = f"/uploads/resumes/{resume_filename}"
        
    # Handle the 6 academic and experience documents
    doc_files = {
        "tenthMarksheet": tenthMarksheet,
        "twelfthMarksheet": twelfthMarksheet,
        "finalSemMarksheet": finalSemMarksheet,
        "provisionalDegreeCertificate": provisionalDegreeCertificate,
        "apprenticeCertificate": apprenticeCertificate,
        "experienceCertificate": experienceCertificate
    }
    
    for doc_key, file_obj in doc_files.items():
        if file_obj:
            doc_filename = f"{student_id}_{doc_key}_{file_obj.filename}"
            doc_path = os.path.join("uploads", "documents", doc_filename)
            with open(doc_path, "wb") as buffer:
                shutil.copyfileobj(file_obj.file, buffer)
            update_data[f"documents.{doc_key}"] = f"/uploads/documents/{doc_filename}"
        
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
    job_dict = job.dict()
    if job.address and (job.address.pincode or job.address.city or job.address.state or job.location):
        lat, lon = get_coordinates_from_pincode(job.address.pincode, job.address.city, job.address.state, job.location)
        job_dict["latitude"] = lat
        job_dict["longitude"] = lon
        
    result = jobs_collection.insert_one(job_dict)
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
    from fastapi.responses import JSONResponse
    import datetime
    if not ObjectId.is_valid(student_id) or not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    student = students_collection.find_one({"_id": ObjectId(student_id)})
    job = jobs_collection.find_one({"_id": ObjectId(job_id)})

    if not student or not job:
        raise HTTPException(status_code=404, detail="Student or Job not found")

    # Check existing application count
    app_doc = applications_collection.find_one({"student_id": student_id, "job_id": job_id})
    apply_count = app_doc.get("apply_count", 0) if app_doc else 0
    if apply_count >= 2:
        return JSONResponse(
            status_code=400,
            content={"message": "Maximum apply attempts reached"}
        )

    # Upsert application to increment apply_count
    applications_collection.update_one(
        {"student_id": student_id, "job_id": job_id},
        {
            "$inc": {"apply_count": 1},
            "$set": {
                "application_status": "applied",
                "applied_date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
        },
        upsert=True
    )

    # Fetch updated application to return its _id
    updated_app = applications_collection.find_one({"student_id": student_id, "job_id": job_id})

    return {
        "message": "Application submitted successfully",
        "application_id": str(updated_app["_id"])
    }

@app.get("/students/{student_id}/applications")
def get_student_applications(student_id: str):
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student id")
    
    student = students_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    apps = list(applications_collection.find({"student_id": student_id}))
    return serialize_mongo(apps)

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
    student_trades = [e.get("trade") or "" for e in student.get("education", [])]
    student_trades = [t for t in student_trades if t]
    
    student_skills = []
    for e in student.get("education", []):
        skills = e.get("skills")
        if isinstance(skills, list):
            student_skills.extend([s for s in skills if s])
    
    # Gather all experience details
    experiences = []
    for exp in student.get("experience", []):
        title = exp.get("jobTitle") or ""
        company = exp.get("companyName") or ""
        desc = exp.get("jobDescription") or ""
        experiences.append(f"{title} at {company}: {desc}")
    
    student_text = f"Full Name: {student.get('fullName') or ''}\nTrades: {', '.join(student_trades)}\nSkills: {', '.join(student_skills)}\nExperience: {' | '.join(experiences)}"


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
        
        final_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for idx, job_id in enumerate(results["ids"][0]):
                job = jobs_collection.find_one({"_id": ObjectId(job_id)})
                if job:
                    # 2. Evaluate with Hybrid Skill Matching Approach (Exact + Semantic)
                    final_score, location_priority, distance_km = calculate_job_match(student, job, return_priority=True)
                    final_results.append(
                        (
                            job,
                            round(final_score, 2),
                            location_priority,
                            distance_km
                        )
                    )
            
            # 3. Sort strictly by final score in descending order
            final_results.sort(
                key=lambda x: x[1],   # final score
                reverse=True
            )
            
            # Format and slice to top 5
            for job, score, priority, distance_km in final_results[:5]:
                trade = job.get("trade", "")
                company = job.get("company") or (trade.capitalize() + " Industry" if trade else "Unknown Company")
                recommendations.append({
                    "job_id": str(job["_id"]),
                    "job_title": job.get("jobTitle", job.get("job_title", "Untitled")),
                    "company": company,
                    "trade": trade,
                    "score": score,
                    "location_priority": priority,
                    "distance_km": round(distance_km, 2) if distance_km is not None else None,
                    "location": job.get("location") or job.get("address", {}).get("city") or "Remote",
                    "experienceLevel": job.get("experienceLevel") or job.get("min_experience") or 0,
                    "jobType": job.get("jobType") or "Full-time",
                    "requiredSkills": job.get("requiredSkills") or [],
                    "jobDescription": job.get("jobDescription") or job.get("description") or "",
                    "salary": job.get("salary") or "Competitive",
                    "employerId": job.get("employerId", ""),
                    "address": job.get("address", {}),
                    "locations": job.get("locations", []),
                    "numberOfVacancies": job.get("numberOfVacancies", 1),
                    "responsibilities": job.get("responsibilities", []),
                    "preferredSkills": job.get("preferredSkills", []),
                    "educationLevel": job.get("educationLevel", ""),
                    "certifications": job.get("certifications", []),
                    "experienceRequirements": job.get("experienceRequirements", ""),
                    "benefits": job.get("benefits", []),
                    "status": job.get("status", "active")
                })
    else:
        # Fallback: Manual skill matching for all jobs
        all_jobs = list(jobs_collection.find())
        final_results = []
        for job in all_jobs:
            final_score, location_priority, distance_km = calculate_job_match(student, job, return_priority=True)
            final_results.append(
                (
                    job,
                    round(final_score, 2),
                    location_priority,
                    distance_km
                )
            )
        
        # Sort strictly by final score in descending order
        final_results.sort(
            key=lambda x: x[1],   # final score
            reverse=True
        )
        
        # Format and slice to top 5
        for job, score, priority, distance_km in final_results[:5]:
            trade = job.get("trade", "")
            company = job.get("company") or (trade.capitalize() + " Industry" if trade else "Unknown Company")
            recommendations.append({
                "job_id": str(job["_id"]),
                "job_title": job.get("jobTitle", job.get("job_title", "Untitled")),
                "company": company,
                "trade": trade,
                "score": score,
                "location_priority": priority,
                "distance_km": round(distance_km, 2) if distance_km is not None else None,
                "location": job.get("location") or job.get("address", {}).get("city") or "Remote",
                "experienceLevel": job.get("experienceLevel") or job.get("min_experience") or 0,
                "jobType": job.get("jobType") or "Full-time",
                "requiredSkills": job.get("requiredSkills") or [],
                "jobDescription": job.get("jobDescription") or job.get("description") or "",
                "salary": job.get("salary") or "Competitive",
                "employerId": job.get("employerId", ""),
                "address": job.get("address", {}),
                "locations": job.get("locations", []),
                "numberOfVacancies": job.get("numberOfVacancies", 1),
                "responsibilities": job.get("responsibilities", []),
                "preferredSkills": job.get("preferredSkills", []),
                "educationLevel": job.get("educationLevel", ""),
                "certifications": job.get("certifications", []),
                "experienceRequirements": job.get("experienceRequirements", ""),
                "benefits": job.get("benefits", []),
                "status": job.get("status", "active")
            })

    return serialize_mongo({
        "student": student["fullName"],
        "recommendations": recommendations
    })

@app.post("/interview/start/{student_id}/{job_id}")
def start_interview(student_id: str, job_id: str):
    from fastapi.responses import JSONResponse
    import datetime
    import random
    import json

    if not ObjectId.is_valid(student_id) or not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    student = students_collection.find_one({"_id": ObjectId(student_id)})
    job = jobs_collection.find_one({"_id": ObjectId(job_id)})

    if not student or not job:
        raise HTTPException(status_code=404, detail="Student or Job not found")

    # Check existing application count
    app_doc = applications_collection.find_one({"student_id": student_id, "job_id": job_id})
    apply_count = app_doc.get("apply_count", 0) if app_doc else 0
    if apply_count >= 2:
        return JSONResponse(
            status_code=400,
            content={"message": "Maximum apply attempts reached"}
        )

    # Upsert application to increment apply_count
    applications_collection.update_one(
        {"student_id": student_id, "job_id": job_id},
        {
            "$inc": {"apply_count": 1},
            "$set": {
                "application_status": "applied",
                "applied_date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
        },
        upsert=True
    )

    # Retrieve MCQ bank for the job (reuse if exists)
    job_id_str = str(job["_id"])  # Ensure string for lookup
    mcq_bank_doc = interviews_collection.find_one({"type": "job_mcq_bank", "job_id": job_id_str})
    if mcq_bank_doc:
        all_questions = mcq_bank_doc["questions"]
    else:
        # Generate and store 15 questions via LLM
        llm_output = generate_interview_questions(student, job)
        try:
            all_questions = json.loads(llm_output)
        except Exception as e:
            print("LLM RAW OUTPUT:", llm_output)
            raise HTTPException(status_code=500, detail="LLM returned invalid JSON")
    if not isinstance(all_questions, list) or len(all_questions) == 0:
        raise HTTPException(status_code=500, detail="No interview questions available")
    # Randomly select ONLY 5 questions
    num_to_sample = min(5, len(all_questions))
    selected_questions = random.sample(all_questions, num_to_sample)

    # Store in new interview_questions collection
    interview_questions_data = {
        "student_id": student_id,
        "job_id": job_id,
        "questions": [
            {
                "question": q["question"],
                "options": q["options"],
                "correct_answer": q["correct_answer"]
            }
            for q in selected_questions
        ],
        "created_at": datetime.datetime.utcnow()
    }
    
    q_result = interview_questions_collection.insert_one(interview_questions_data)
    interview_id = str(q_result.inserted_id)

    # Return only those 5 questions (without correct_answer) to frontend
    return {
        "interview_id": interview_id,
        "questions": [
            {
                "question": q["question"],
                "options": q["options"]
            }
            for q in selected_questions
        ]
    }


@app.get("/interview/{interview_id}")
def get_interview(interview_id: str):

    interview = interview_questions_collection.find_one({"_id": ObjectId(interview_id)})

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return {
        "questions": [
            {
                "question": q["question"],
                "options": q["options"]
            }
            for q in interview["questions"]
        ]
    }



class Answer(BaseModel):
    question: str
    answer: str

class InterviewSubmission(BaseModel):
    answers: List[Answer]



@app.post("/interview/submit/{interview_id}")
def submit_interview(interview_id: str, submission: InterviewSubmission):

    interview = interview_questions_collection.find_one({"_id": ObjectId(interview_id)})

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    total_correct = 0
    num_questions = len(interview.get("questions", []))

    if num_questions == 0:
        raise HTTPException(status_code=400, detail="No questions found")

    # 🔹 MCQ Scoring
    scored_answers = []
    for i, ans in enumerate(submission.answers):
        stored_q = interview["questions"][i]
        
        # Robust comparison for MCQ answers:
        # Handles option letters (e.g. "Option A", "A"), option text, or direct match.
        is_correct = False
        student_ans_clean = ans.answer.strip().lower()
        correct_ans_clean = stored_q["correct_answer"].strip().lower()
        options = stored_q.get("options", [])
        
        # 1. Direct text match
        if student_ans_clean == correct_ans_clean:
            is_correct = True
        else:
            # 2. Check if correct_answer represents an option index/letter (e.g. "Option A", "A")
            letter = None
            if correct_ans_clean in ['a', 'b', 'c', 'd']:
                letter = correct_ans_clean
            elif correct_ans_clean.startswith('option'):
                rem = correct_ans_clean[6:].strip(" :-")
                if rem and rem[0] in ['a', 'b', 'c', 'd']:
                    letter = rem[0]
            
            if letter is not None:
                idx = ord(letter) - ord('a')
                if 0 <= idx < len(options):
                    if student_ans_clean == options[idx].strip().lower():
                        is_correct = True
            
            # 3. Fallback: if student's answer text matches option text that matches correct_answer
            if not is_correct:
                for idx, opt in enumerate(options):
                    opt_clean = opt.strip().lower()
                    if opt_clean and (opt_clean in correct_ans_clean or correct_ans_clean in opt_clean):
                        if student_ans_clean == opt_clean:
                            is_correct = True
                            break

        # Make display-friendly correct answer string for the report (e.g. "Option A (Check for overloaded circuits)")
        correct_answer_display = stored_q["correct_answer"]
        letter = None
        if correct_ans_clean in ['a', 'b', 'c', 'd']:
            letter = correct_ans_clean
        elif correct_ans_clean.startswith('option'):
            rem = correct_ans_clean[6:].strip(" :-")
            if rem and rem[0] in ['a', 'b', 'c', 'd']:
                letter = rem[0]
        
        if letter is not None:
            idx = ord(letter) - ord('a')
            if 0 <= idx < len(options):
                correct_answer_display = f"{stored_q['correct_answer']} ({options[idx]})"
        
        if is_correct:
            total_correct += 1
            
        scored_answers.append({
            "question": stored_q["question"],
            "student_answer": ans.answer,
            "correct_answer": correct_answer_display,
            "is_correct": is_correct
        })

    # 🔹 Interview Score (Percentage)
    interview_score = round((total_correct / num_questions) * 100, 2)

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

    # 🔹 Store in interview_results collection
    result_data = {
        "interview_id": interview_id,
        "student_id": interview["student_id"],
        "job_id": interview["job_id"],
        "answers": scored_answers,
        "final_score": final_score,
        "interview_score": interview_score,
        "job_match_score": job_match_score,
        "feedback": feedback,
        "timestamp": datetime.utcnow()
    }
    
    # 🔹 Generate PDF Report
    try:
        report_url = generate_interview_report(
            result_data=result_data,
            interview_data=interview,
            student_name=student.get("fullName", "Candidate"),
            job_title=job.get("jobTitle", job.get("job_title", "Position"))
        )
        result_data["report_url"] = report_url
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        report_url = None

    interview_results_collection.insert_one(result_data)

    return {
        "interview_score": interview_score,
        "job_match_score": job_match_score,
        "final_score": final_score,
        "feedback": feedback,
        "report_url": report_url
    }



@app.get("/interview/result/{interview_id}")
def get_result(interview_id: str):

    # Try session collection first (legacy or in-progress)
    interview = interview_results_collection.find_one({"interview_id": interview_id})
    
    # Fallback to general interviews collection
    if not interview:
        interview = interviews_collection.find_one({"_id": ObjectId(interview_id)})

    if not interview:
        raise HTTPException(status_code=404, detail="Interview result not found")
    
    return {
        "student_id": str(interview.get("student_id")),
        "interview_score": interview.get("interview_score", 0),
        "job_match_score": interview.get("job_match_score", 0),
        "final_score": interview.get("final_score", interview.get("score", 0)),
        "feedback": interview.get("feedback", "Pending"),
        "report_url": interview.get("report_url")
    }
