# NEXUS

NEXUS is an autonomous AI and technology editorial persona. It continuously monitors the AI and technology ecosystem and decides which developments are actually worth discussing. It acts as an independent, skeptical, and analytical AI systems analyst.

Currently in Phase 1: Foundation.

## Requirements
* Python 3.9+
* A Google Gemini API key

## Setup Instructions

### 1. Create a Python Virtual Environment
Navigate to the project root and create a virtual environment:
```bash
python3 -m venv venv
```

Activate the virtual environment:
* On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```
* On Windows:
  ```bash
  venv\Scripts\activate
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the `.env.example` file to create a `.env` file:
```bash
cp .env.example .env
```

Open `.env` and set your `GEMINI_API_KEY`. DO NOT commit this file to version control.

### 4. Running the Application

To start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

To test the `/health` endpoint:
```bash
curl http://localhost:8000/health
```
You should see: `{"status": "ok", "service": "NEXUS"}`

### 5. Running the Gemini Test

To verify the Gemini API connection:
```bash
python test_gemini.py
```
This script will output a short response from Gemini to verify that the provider is working correctly.
