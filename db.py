import os
import subprocess
import time
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import chromadb

# Load environment variables from .env
load_dotenv()

# Get MONGO_URI from .env, default to localhost if not set
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

def start_mongodb_if_needed(uri):
    # Test connection with a short timeout
    temp_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    try:
        # Ping the database to confirm it's running
        temp_client.admin.command('ping')
    except ServerSelectionTimeoutError:
        print("MongoDB connection failed. Attempting to start MongoDB automatically...")
        
        mongo_path = r"C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe"
        db_path = os.path.join(os.getcwd(), "mongo_data")
        
        if not os.path.exists(db_path):
            os.makedirs(db_path)
        
        # Start mongod in a new detached console window
        try:
            subprocess.Popen([mongo_path, "--dbpath", db_path], 
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            print("MongoDB process started. Waiting for it to initialize...")
            time.sleep(3) # Wait for mongod to start
        except Exception as e:
            print(f"Failed to start MongoDB automatically: {e}")
            print(f"Please run it manually: '{mongo_path}' --dbpath '{db_path}'")

# Check and start if necessary (only for local connections)
if "localhost" in MONGO_URI or "127.0.0.1" in MONGO_URI:
    start_mongodb_if_needed(MONGO_URI)

# Database connection
client = MongoClient(MONGO_URI)
db = client["test"] # Switched to production DB name found in Atlas search

students_collection = db["candidateprofiles"] # Correct production candidate collection
jobs_collection = db["jobposts"] # Correct production job collection
interviews_collection = db["interviews"]
applications_collection = db["applications"]

# ENABLING CHROMADB
chroma_client = chromadb.PersistentClient(path="./chroma_db_new")
jobs_vector_collection = chroma_client.get_or_create_collection(name="jobs_collection")
