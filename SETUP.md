# ⚙️ GeoPilot / AIVOP Local Setup Guide

Follow this guide to set up the **GeoPilot** application locally for development and testing.

---

## 1. Prerequisites

Before installing, ensure you have the following installed on your machine:
*   **Python**: Version 3.10 or 3.11
*   **Node.js**: Version 18.x or 20.x (with `npm`)
*   **Redis**: Runs locally or via a Docker container (required for Celery tasks and caching)
*   **Supabase Database**: A Supabase workspace (PostgreSQL)

---

## 2. Configuration Settings

### 2.1. Backend Configuration (`backend/.env`)
Create a `.env` file in the `backend/` directory:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GEMINI_API_KEY=AIzaSy...
REDIS_URL=redis://127.0.0.1:6379/0
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 2.2. Frontend Configuration (`frontend/.env.local`)
Create a `.env.local` file in the `frontend/` directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 3. Database Initializer (Supabase)

1.  Open the **Supabase Dashboard** for your project.
2.  Go to the **SQL Editor** tab.
3.  Load the contents of the `database/schema.sql` file.
4.  Execute the script to create the tables, indexes, and configure the Row-Level Security (RLS) policies.

---

## 4. Backend Setup (FastAPI)

1.  **Open terminal inside the `backend` folder**:
    ```bash
    cd backend
    ```
2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Start Redis Server** (via Docker or local client):
    ```bash
    docker run -d -p 6379:6379 redis
    ```
5.  **Start the Celery worker pool**:
    ```bash
    celery -A app.core.celery_app worker --loglevel=info
    ```
6.  **Run the FastAPI web server**:
    ```bash
    python -m uvicorn app.main:app --port 8000 --reload
    ```

---

## 5. Frontend Setup (Next.js)

1.  **Open terminal inside the `frontend` folder**:
    ```bash
    cd ../frontend
    ```
2.  **Install dependencies**:
    ```bash
    npm install
    ```
3.  **Launch the Next.js development server**:
    ```bash
    npm run dev
    ```
4.  Open [http://localhost:3000](http://localhost:3000) inside your web browser.
