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

def get_location_match_and_priority(student, job):
    """
    Computes location match score, priority level, and distance based on coordinates
    with fallback to textual matching.
    Returns: (location_score, location_priority, distance_km)
    """
    from services.location_service import calculate_distance, get_location_score
    
    student_lat = student.get("latitude")
    student_lon = student.get("longitude")
    job_lat = job.get("latitude")
    job_lon = job.get("longitude")
    
    # 1. Coordinate-based matching
    if student_lat is not None and student_lon is not None and job_lat is not None and job_lon is not None:
        distance_km = calculate_distance((student_lat, student_lon), (job_lat, job_lon))
        if distance_km is not None:
            score = get_location_score(distance_km)
            # Map distance to priority
            if distance_km <= 10.0:
                priority = 3
            elif distance_km <= 50.0:
                priority = 2
            elif distance_km <= 200.0:
                priority = 1
            else:
                priority = 0
            return score, priority, distance_km

    # 2. Textual Fallback if coordinates missing/failed
    student_city = (student.get("city") or "").strip().lower()
    student_state = (student.get("state") or "").strip().lower()
    
    job_addr = job.get("address") or {}
    job_city = (job_addr.get("city") or job.get("location") or "").strip().lower()
    job_state = (job_addr.get("state") or "").strip().lower()
    
    if student_city and job_city and student_city == job_city:
        return 70, 3, None
    elif student_state and job_state and student_state == job_state:
        return 40, 1, None
        
    return 0, 0, None


def calculate_job_match(student, job, return_priority=False):
    # Pull skills from ALL education entries
    student_skills = []
    education_entries = student.get("education", []) or []
    for e in education_entries:
        skills = e.get("skills")
        if isinstance(skills, list):
            student_skills.extend([s for s in skills if s])
    
    # If no explicit skills, pull from trade names
    if not student_skills:
        student_skills = [e.get("trade") or "" for e in education_entries]
        student_skills = [t for t in student_skills if t]
        
    job_skills = job.get("requiredSkills") or []
    if not isinstance(job_skills, list):
        job_skills = []
    job_skills = [s for s in job_skills if s]
    
    # Get the raw similarity and exact overlap out of 100
    semantic_score, exact_match_score = get_skill_components(student_skills, job_skills)
    
    # Calculate 'Other' metrics (Trade, Experience, Location)
    # Check all trades from education list
    student_trades = [e.get("trade") or "" for e in education_entries]
    student_trades = [t.lower() for t in student_trades if t]
    
    job_title = (job.get("jobTitle") or job.get("job_title") or "").lower()
    job_trade = (job.get("trade") or "").lower()
    job_desc = (job.get("jobDescription") or "").lower()
    
    # Trade match: check if ANY of student's trades are relevant to the job
    trade_match = 0
    for st in student_trades:
        if st and (st in job_title or st in job_desc or st == job_trade):
            trade_match = 100
            break
    
    # Experience match: 
    # Calculate total experience years from the experience list
    experience_entries = student.get("experience", []) or []
    total_exp_years = len(experience_entries) # simple heuristic: count roles
    
    job_exp_level = job.get("experienceLevel", "Fresher") or "Fresher"
    
    if job_exp_level == "Fresher":
        exp_score = 100 if total_exp_years <= 1 else 50
    else:  # Experienced
        exp_score = 100 if total_exp_years >= 1 else 0
        
    # Get location score, priority level, and distance
    location_score, location_priority, distance_km = get_location_match_and_priority(student, job)
    
    # Final Score formula under new specifications:
    # final_score = (0.50 * semantic_score) + (0.25 * exact_match_score) + (0.05 * trade_match) + (0.05 * exp_score) + (0.15 * location_score)
    final_score = (
        (0.50 * semantic_score) +
        (0.25 * exact_match_score) +
        (0.05 * trade_match) +
        (0.05 * exp_score) +
        (0.15 * location_score)
    )
    
    final_score_rounded = round(final_score, 2)
    
    if return_priority:
        return final_score_rounded, location_priority, distance_km
    return final_score_rounded

