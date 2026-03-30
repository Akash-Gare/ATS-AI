# ATS AI - Applicant Tracking System & Interview Simulator

Welcome to the **ATS AI** project! This is a backend and frontend application for a RAG-enabled Candidate Matching System and an LLM-Powered Interview Grader.

## Features
- **Job Posting & Semantic Matching**: Recruiters post jobs which are saved in MongoDB and embedded into ChromaDB for semantic search.
- **Candidate Skill Matching**: A hybrid skill match algorithm comparing student profiles against required job skills.
- **AI-Powered Interviews**: Dynamic interview scenarios generated via Groq (`llama-3.3-70b`) based on the specific job description and the candidate's skillset.
- **Automated Grading**: Interview answers are evaluated for correctness, completeness, and technical accuracy.

## Tech Stack
- **Backend Framework**: Python (FastAPI, Uvicorn)
- **Database**: MongoDB (Local)
- **Vector Store**: ChromaDB
- **LLM Integrations**: Groq API (`llama-3.3-70b`)

## Prerequisites
- **Python 3.8+**
- **MongoDB** running in the background (`localhost:27017`).

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone YOUR_GITHUB_REPO_URL
   cd ATS_AI
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv atsenv
   atsenv\Scripts\activate  # On Windows
   # source atsenv/bin/activate  # On macOS/Linux
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and add the following:
   ```env
   GROQ_API_KEY="your_groq_api_key_here"
   MONGO_URI="mongodb://localhost:27017/"
   ```

## Running the Application

Start the development server using Uvicorn:
```bash
python -m uvicorn app:app --port 8080 --reload
```
*(We use port 8080 by default because port 8000 often causes "Access Forbidden" errors on Windows if it is already used by another service).*

## Usage & API Documentation

FastAPI provides an interactive API console (Swagger UI) automatically. 

Once your server is running, open your web browser and go to:
[http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

From there, you can directly interact with the API endpoints.

### Key API Workflows:
1. **Create a Job (`POST /jobs/post`)**: Injects a job description into MongoDB & creates embeddings inside ChromaDB.
2. **Get Recommendations (`GET /recommend/{student_id}`)**: Retrieves job recommendations for a specific student running the hybrid skill match algorithm.
3. **Start an Interview (`POST /interview/start/{student_id}/{job_id}`)**: Generates dynamic interview questions based on the candidate and job role.
4. **Submit Interview Answers (`POST /interview/submit/{interview_id}`)**: Pass answers to the AI to get graded on specific success criteria.
