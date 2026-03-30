from sentence_transformers import SentenceTransformer, util
import os

# Load model once (IMPORTANT)
model = SentenceTransformer('all-MiniLM-L6-v2')



def get_skill_components(student_skills, job_required_skills):
    if not student_skills or not job_required_skills:
        return 0.0, 0.0

    # 1. Exact Skill Matching (Skill Overlap)
    student_skills_set = set(str(s).lower().strip() for s in student_skills)
    job_skills_set = set(str(s).lower().strip() for s in job_required_skills)

    if not job_skills_set:
        skill_match_score = 0.0
    else:
        overlap = student_skills_set.intersection(job_skills_set)
        skill_match_score = (len(overlap) / len(job_skills_set)) * 100.0

    # 2. Semantic Skill Matching
    student_text = " ".join(student_skills)
    job_text = " ".join(job_required_skills)

    embeddings = model.encode([student_text, job_text], convert_to_tensor=True)
    similarity = util.cos_sim(embeddings[0], embeddings[1])
    semantic_score = float(similarity[0][0]) * 100.0
    
    # Threshold filter
    if semantic_score < 30.0:
        semantic_score = 0.0
    semantic_score = max(0.0, min(100.0, semantic_score))
    
    return semantic_score, skill_match_score

def calculate_skills_similarity(student_skills, job_required_skills):
    # Used if app.py strictly just asks for a 0-100 skill score (scales 60/30 up)
    sem, exact = get_skill_components(student_skills, job_required_skills)
    return round((0.66 * sem) + (0.34 * exact), 2)

def calculate_job_match(student, job):
    # Pull skills from ALL education entries
    student_skills = []
    for e in student.get("education", []):
        student_skills.extend(e.get("skills", []))
    
    # If no explicit skills, pull from trade names
    if not student_skills:
        student_skills = [e.get("trade", "") for e in student.get("education", [])]
        
    job_skills = job.get("requiredSkills", [])
    
    # Get the raw similarity and exact overlap out of 100
    semantic_score, exact_match_score = get_skill_components(student_skills, job_skills)
    
    # Calculate 'Other' metrics (Trade, Experience, Location)
    # Check all trades from education list
    student_trades = [e.get("trade", "").lower() for e in student.get("education", [])]
    
    job_title = job.get("jobTitle", "").lower()
    job_trade = job.get("trade", "").lower()
    job_desc = job.get("jobDescription", "").lower()
    
    # Trade match: check if ANY of student's trades are relevant to the job
    trade_match = 0
    for st in student_trades:
        if st and (st in job_title or st in job_desc or st == job_trade):
            trade_match = 100
            break
    
    # Experience match: 
    # Calculate total experience years from the experience list
    total_exp_years = len(student.get("experience", [])) # simple heuristic: count roles
    # Better: each role is roughly 1-2 years? Or just check if they HAVE experience for "Experienced" jobs.
    job_exp_level = job.get("experienceLevel", "Fresher")
    
    if job_exp_level == "Fresher":
        exp_score = 100 if total_exp_years <= 1 else 50
    else:  # Experienced
        exp_score = 100 if total_exp_years >= 1 else 0
        
    student_city = student.get("city", "").lower()
    student_state = student.get("state", "").lower()
    
    job_addr = job.get("address", {})
    job_city = str(job_addr.get("city", "")).lower()
    
    loc_match = 100 if (student_city and job_city and student_city == job_city) else 0
    
    # Average the other attributes together
    other_score = (trade_match + exp_score + loc_match) / 3.0
    
    # Final Score spec: 60% similarity, 30% skill overlapping, 10% other
    final_score = (0.60 * semantic_score) + (0.30 * exact_match_score) + (0.10 * other_score)
    
    return round(final_score, 2)
