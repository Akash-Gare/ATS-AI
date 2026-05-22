import sys
import os
sys.path.append(os.getcwd())

from bson import ObjectId
from db import students_collection, jobs_collection, jobs_vector_collection
from app import get_recommendations

students = list(students_collection.find())
print(f"Found {len(students)} students in MongoDB:")
for s in students:
    s_id = str(s['_id'])
    print(f"\nStudent Name: {s.get('fullName')} | ID: {s_id}")
    print(f"  Education Trades: {[e.get('trade', '') for e in s.get('education', [])]}")
    skills = []
    for e in s.get('education', []):
        skills.extend(e.get('skills', []))
    print(f"  Education Skills: {skills}")
    
    # Let's see recommendations
    res = get_recommendations(s_id)
    recs = res.get('recommendations', [])
    print(f"  Total Recommendations returned: {len(recs)}")
    for idx, r in enumerate(recs):
        print(f"    {idx+1}. Job: {r['job_title']} | Company: {r['company']} | Score: {r['score']}")
