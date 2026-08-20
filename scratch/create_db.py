import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

# Make sure we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("MONGO_URI not found in environment variables.")
    sys.exit(1)

client = MongoClient(MONGO_URI)
db = client["ats_ai"]

collections_to_create = [
    "candidateprofiles",
    "jobposts",
    "interviews",
    "interview_questions",
    "interview_results",
    "applications",
    "question_bank"
]

print(f"Connected to MongoDB Atlas. Creating database 'ats_ai' and collections...")

for coll_name in collections_to_create:
    try:
        db.create_collection(coll_name)
        print(f"Created collection: {coll_name}")
    except Exception as e:
        print(f"Collection {coll_name} might already exist or error occurred: {e}")

# Create index on interviews collection to match db.py
try:
    db["interviews"].create_index("type")
    print("Created index on 'interviews' collection.")
except Exception as e:
    print(f"Failed to create index: {e}")

print("\nAll done! You can now refresh MongoDB Compass to see your new 'ats_ai' database and its collections.")
