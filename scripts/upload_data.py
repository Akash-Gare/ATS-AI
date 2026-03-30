import requests
import json

import os

base_dir = os.path.dirname(__file__)
data_file = os.path.join(base_dir, "..", "data", "sample_iti_data.json")

with open(data_file, "r") as f:
    students = json.load(f)

for student in students:
    url = 'http://127.0.0.1:8000/students/register'
    resp = requests.post(url, json=student)
    if resp.status_code == 200:
        print(f"Registered: {student['name']} - ID: {resp.json().get('student_id')}")
    else:
        print(f"Failed to register {student['name']}: {resp.text}")
