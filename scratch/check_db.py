import sys
import os
from bson import ObjectId

# Adjust path to import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import db

def check_records():
    print("=== Students (candidateprofiles) in DB ===")
    for student in db.candidateprofiles.find():
        print(f"Name: {student.get('fullName')}")
        print(f"  Pincode: {student.get('pinCode') or student.get('pincode')}")
        print(f"  City: {student.get('city')}, State: {student.get('state')}")
        print(f"  Coordinates: Lat={student.get('latitude')}, Lon={student.get('longitude')}")
        print("-" * 30)

    print("\n=== Jobs (jobposts) in DB ===")
    for job in db.jobposts.find():
        print(f"Title: {job.get('jobTitle') or job.get('job_title')}")
        print(f"  Company: {job.get('company')}")
        print(f"  Address: {job.get('address')}")
        print(f"  Coordinates: Lat={job.get('latitude')}, Lon={job.get('longitude')}")
        print("-" * 30)

if __name__ == "__main__":
    check_records()
