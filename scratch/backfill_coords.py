import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import db
from services.location_service import get_coordinates_from_pincode

def backfill():
    print("=== Backfilling Student coordinates ===")
    student_count = 0
    for student in db.candidateprofiles.find():
        student_id = student["_id"]
        # If coordinates are missing, backfill them
        if student.get("latitude") is None or student.get("longitude") is None:
            pincode = student.get("pinCode") or student.get("pincode")
            city = student.get("city")
            state = student.get("state")
            
            if pincode or city or state:
                lat, lon = get_coordinates_from_pincode(pincode, city, state)
                if lat is not None and lon is not None:
                    db.candidateprofiles.update_one(
                        {"_id": student_id},
                        {"$set": {"latitude": lat, "longitude": lon}}
                    )
                    print(f"Updated Student: {student.get('fullName')} with Lat={lat}, Lon={lon}")
                    student_count += 1
                else:
                    print(f"Could not resolve location for Student: {student.get('fullName')} (Pincode={pincode}, City={city})")
    
    print(f"\nTotal Students updated: {student_count}")
    
    print("\n=== Backfilling Job coordinates ===")
    job_count = 0
    for job in db.jobposts.find():
        job_id = job["_id"]
        if job.get("latitude") is None or job.get("longitude") is None:
            address = job.get("address") or {}
            pincode = address.get("pincode")
            city = address.get("city") or job.get("location")
            state = address.get("state")
            
            if pincode or city or state:
                lat, lon = get_coordinates_from_pincode(pincode, city, state)
                if lat is not None and lon is not None:
                    db.jobposts.update_one(
                        {"_id": job_id},
                        {"$set": {"latitude": lat, "longitude": lon}}
                    )
                    print(f"Updated Job: {job.get('jobTitle')} ({job.get('company')}) with Lat={lat}, Lon={lon}")
                    job_count += 1
                else:
                    print(f"Could not resolve location for Job: {job.get('jobTitle')} (Pincode={pincode}, City={city})")
                    
    print(f"\nTotal Jobs updated: {job_count}")

if __name__ == "__main__":
    backfill()
