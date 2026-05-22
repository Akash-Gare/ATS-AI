import sys
import os
sys.path.append(os.getcwd())

from app import Job, Address, Salary

def test_job_validation():
    sample_payload = {
        "company": "Tech Solutions Ltd",
        "employerId": "emp_001",
        "jobTitle": "Junior Computer Operator",
        "trade": "computer operator",
        "jobType": "Full time",
        "experienceLevel": "Fresher",
        "address": {
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411001"
        },
        "locations": ["Pune"],
        "location": "Pune",
        "salary": {
            "min": 15000,
            "max": 25000
        },
        "numberOfVacancies": 2,
        "jobDescription": "We are looking for a Computer Operator with proficiency in MS Office.",
        "responsibilities": [
            "Data entry and management",
            "Preparing reports in Excel",
            "Handling office documentation"
        ],
        "requiredSkills": [
            "MS Office",
            "Excel",
            "Data Entry",
            "Typing"
        ],
        "preferredSkills": [
            "English Communication",
            "Problem Solving"
        ],
        "educationLevel": "Graduate",
        "certifications": [
            "MS-CIT"
        ],
        "experienceRequirements": "0-1 years",
        "min_experience": 0,
        "benefits": [
            "Medical Insurance",
            "Paid Leaves"
        ],
        "status": "active"
    }

    try:
        job = Job(**sample_payload)
        print("Success: Job validated successfully by Pydantic!")
        print("Company:", job.company)
        print("Employer ID:", job.employerId)
        print("Address Object:", job.address)
        print("Salary Object:", job.salary)
        print("Locations:", job.locations)
        print("Experience Requirements:", job.experienceRequirements)
        print("Status:", job.status)
        assert job.address.city == "Pune"
        assert job.salary.min == 15000
        assert job.locations == ["Pune"]
        print("Assertions passed perfectly!")
    except Exception as e:
        print("Error: Validation failed!")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    test_job_validation()
