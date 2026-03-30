# ATS AI API Guide

This is your backend server for the RAG-enabled Candidate Matching System & LLM-Powered Interview Grader.

## 1. Prerequisites (What you need installed)
- **Python 3.8+**
- **MongoDB** running in the background. (By default our `db.py` logic tries pointing strictly to `localhost:27017` and attempts starting Mongo on `C:\Program Files\MongoDB\Server\8.2\...` automatically if it is turned off).

## 2. API Key Configuration
Your project relies on having a `.env` file at the root folder `C:\Users\sahil\ATS_AI\ATS_AI\.env`.
It must contain:
```ini
GROQ_API_KEY="your_groq_api_key_here"
MONGO_URI="mongodb://localhost:27017/"
```

## 3. How to Start the Server
Open your terminal (in VS Code or Command Prompt). Navigate to the `ATS_AI` project folder and run:

```bash
python -m uvicorn app:app --port 8080 --reload
```
*(We use port 8080 because port 8000 often causes "Access Forbidden" errors on Windows if it is already used by another service).*

## 4. How to Test Your Endpoints Live
Instead of using Postman, FastAPI has an interactive console generated automatically!

Once your terminal says `Uvicorn running on http://127.0.0.1:8080`, open your web browser and go to:
[http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

From that Swagger UI, you can directly click **"Try it out"** on any endpoint! Let's walk through the order of operations:

### Endpoint Flow:

**A. Create a Job (`POST /jobs/post`)**
Use this to inject a job description into MongoDB & create embeddings inside ChromaDB.
**Example JSON Body:**
```json
{
  "recruiter_id": "12345",
  "job_title": "Senior Fitter",
  "company": "Tata Motors",
  "description": "Looking for a skilled fitter for assembly and machining.",
  "location": "Pune",
  "required_skills": ["machining", "welding", "assembly"],
  "min_experience": 2
}
```

**B. Get Recommendations (`GET /recommend/{student_id}`)**
This runs the Hybrid skill match algorithm! Pass any valid MongoDB student object ID inside the URL. It executes the semantic overlap vs exact matcher pipeline scoring output.

**C. Start an Interview (`POST /interview/start/{student_id}/{job_id}`)**
This invokes the LLM (`llama-3.3-70b`)! It matches the Student's skills to the Job's description and dynamically outputs 5 tiny scenarios. It responds with the `interview_id`.

**D. Submit Interview Answers (`POST /interview/submit/{interview_id}`)**
Pass the answers to questions generated above! They are fed through `llm_service.py` to get graded based strictly on *1. correctness*, *2. completeness*, and *3. technical accuracy*. Returns final score.
