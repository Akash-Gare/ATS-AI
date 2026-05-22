import sys
import os
sys.path.append(os.getcwd())

from app import Student, Education, Experience, Preferences

def test_student_and_docs_validation():
    print("Testing Student and Documents schema validation...")
    
    student_payload = {
        "userId": "candidate@example.com",
        "fullName": "Jane Doe",
        "email": "candidate@example.com",
        "password": "hashed_password",
        "mobile": "9876543210",
        "dob": "1998-05-15",
        "city": "Pune",
        "state": "Maharashtra",
        "pinCode": "411045",
        "area": "Baner",
        "taluka": "Haveli",
        "district": "Pune",
        "trade": "Electrical Engineering",
        "skills": ["Wiring", "Troubleshooting", "CAD"],
        "profilePhoto": "/uploads/profile_pics/sample.jpg",
        "documents": {
            "tenthMarksheet": "/uploads/documents/sample_tenth.pdf",
            "twelfthMarksheet": "/uploads/documents/sample_twelfth.pdf",
            "finalSemMarksheet": None,
            "provisionalDegreeCertificate": None,
            "apprenticeCertificate": None,
            "experienceCertificate": None
        },
        "education": [
            {
                "educationType": "Degree",
                "boardName": "SPPU",
                "trade": "Electrical",
                "skills": ["Power Systems"],
                "instituteName": "COEP",
                "passingYear": 2020,
                "rollNumber": "E190023",
                "certificateNumber": "CERT88291"
            }
        ],
        "experience": [
            {
                "companyName": "Tesla Motors",
                "jobTitle": "Electrical Engineer Intern",
                "isCurrentlyWorking": False,
                "employmentType": "Full time",
                "jobDescription": "Assisted with power distribution layout designs."
            }
        ],
        "preferences": {
            "expectedSalary": "35000",
            "preferredLocations": "Pune"
        },
        "isProfileComplete": True
    }
    
    try:
        student = Student(**student_payload)
        print("Success: Student and Documents validated perfectly by Pydantic!")
        assert student.documents.get("tenthMarksheet") == "/uploads/documents/sample_tenth.pdf"
        assert student.documents.get("finalSemMarksheet") is None
        assert len(student.education) == 1
        assert student.education[0].rollNumber == "E190023"
        print("All student schema assertions passed successfully!")
    except Exception as e:
        print("Error: Student schema validation failed!")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    test_student_and_docs_validation()
