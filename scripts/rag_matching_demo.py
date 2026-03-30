import os
import sys
from typing import List, Dict, Any

# Ensure local imports work correctly without red lines
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bson import ObjectId
from db import students_collection, jobs_collection, jobs_vector_collection
from services.scoring_service import calculate_job_match

def run_rag_pipeline(student_id):
    # 1. Fetch data from MongoDB
    print(f"--- 1. Fetching Job Data from MongoDB ---")
    jobs = list(jobs_collection.find())
    print(f"Fetched {len(jobs)} jobs from MongoDB.\n")
    
    # 2. Convert Job Data to Text & Store Embeddings in ChromaDB (RAG Logic)
    print(f"--- 2. Converting to Text Document & Storing Embeddings in ChromaDB ---")
    count: int = 0
    for job in jobs:
        job_id = str(job["_id"])
        skills_str = ", ".join(job.get("required_skills", []))
        
        # Convert data to a text document formulation
        job_text = f"Job Title: {job.get('job_title', '')}\nSkills: {skills_str}\nDescription: {job.get('description', '')}"
        
        try:
            # Store embedding in ChromaDB
            jobs_vector_collection.upsert(
                documents=[job_text],
                ids=[job_id],
                metadatas=[{
                    "job_title": job.get("job_title", ""),
                    "company": job.get("company", "")
                }]
            )
            count += 1
        except Exception as e:
            print(f"Failed to embed job {job_id}: {e}")
            
    print(f"Successfully created and stored embeddings for {count} jobs in ChromaDB.\n")

    # 3. Match Job and Student Skills using ChromaDB (RAG Query)
    print(f"--- 3. Fetching Student & Matching Skills ---")
    student = students_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        print("Student not found!")
        return
        
    print(f"Evaluating Student: {student.get('name')} (Trade: {student.get('trade')})")
    
    # Convert student skills to text for querying
    student_skills = [s.get("name", "") if isinstance(s, dict) else str(s) for s in student.get("skills", [])]
    skills_str = ", ".join(student_skills)
    student_text = f"Trade: {student.get('trade')}\nSkills: {skills_str}\nExperience: {student.get('experience_years')} years"
    
    print("\nQuerying ChromaDB for most semantically similar jobs...")
    results = jobs_vector_collection.query(
        query_texts=[student_text],
        n_results=min(10, count)  # Get top k matches
    )
    
    recommendations: List[Dict[str, Any]] = []
    if results["ids"] and len(results["ids"][0]) > 0:
        for idx, job_id in enumerate(results["ids"][0]):
            job = jobs_collection.find_one({"_id": ObjectId(job_id)})
            if job:
                # Perform a secondary hard skill match using our custom scoring service
                score = calculate_job_match(student, job)
                recommendations.append({
                    "job_title": job["job_title"],
                    "company": job["company"],
                    "score": round(score, 2),
                    "skills_required": job.get("required_skills")
                })
                
    # 4. Recommend Job
    print(f"\n--- 4. Final Job Recommendations ---")
    # Sort recommendations by the final calculated skill match score
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    # Show Top 5 recommendations
    for idx, rec in enumerate(recommendations[:5]):
        print(f"{idx+1}. {rec['job_title']} at {rec['company']} - Match Score: {rec['score']} / 100")
        print(f"   Required Skills: {rec['skills_required']}")
        print("-" * 50)

if __name__ == "__main__":
    # Get a sample student from MongoDB to test the pipeline
    sample_student = students_collection.find_one()
    if sample_student:
        run_rag_pipeline(str(sample_student["_id"]))
    else:
        print("No students found in MongoDB. Please register a student first.")
