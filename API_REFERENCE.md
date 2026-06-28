# 🔌 GeoPilot / AIVOP API Reference

This document catalogs the REST API endpoints served by the AIVOP backend, organized by modular domains. All endpoints are prefixed with `/api/v1`.

---

## 1. Authentication

All requests must contain an `Authorization` header with a valid Supabase JWT Bearer token:
```http
Authorization: Bearer <jwt-token>
```

For local testing and verification, mock headers are supported:
```http
Authorization: Bearer mock-<user-uuid>
```

---

## 2. Project Management (`projects.py`)

### List Workspace Projects
*   **Method & Path**: `GET /projects/`
*   **Description**: Retrieves all projects owned by the authenticated tenant.
*   **Response**: `List[ProjectDetail]`

### Create New Project
*   **Method & Path**: `POST /projects/`
*   **Body**:
    ```json
    {
      "project_name": "My Brand SaaS",
      "website_url": "https://brand.com"
    }
    ```
*   **Response**: `ProjectDetail`

---

## 3. Modular Analysis Routers

### 3.1. Analysis Aggregates (`analysis_results.py`)
*   **Get Project Results Summary**: `GET /analysis/results/{project_id}`
    *   *Description*: Compiles all facts, competitor benchmark lists, content recommendations, and agent execution runs. Highly cached.

### 3.2. Discovered Questions (`analysis_questions.py`)
*   **Get Paginated Queries**: `GET /analysis/questions/{project_id}`
    *   *Parameters*: `page` (default `1`), `search` (text filter), `question_type` (e.g. `Awareness`).

### 3.3. Keywords Strategy (`analysis_keywords.py`)
*   **Get Keyword Clusters**: `GET /analysis/keywords/{project_id}`

### 3.4. Generative Engine Optimization (`analysis_geo.py`)
*   **GEO Readiness Score**: `GET /analysis/geo-readiness/{project_id}`
*   **Citation Reports**: `GET /analysis/citation-report/{project_id}`
*   **Competitor Matrix Gaps**: `GET /analysis/competitor-recommendations/{project_id}`
*   **Explainable Citation Reasonings**: `GET /analysis/citation-reasoning/{project_id}`

### 3.5. Advanced Analytics (`analysis_analytics.py`)
*   **Competitor benchmarks**: `GET /analysis/competitor-benchmark/{project_id}`
*   **Historical delta trends**: `GET /analysis/historical-metrics/{project_id}`
*   **Regressions & Heatmaps**: `GET /analysis/analytics/{project_id}`

### 3.6. Health & Reality Checks (`analysis_reliability.py`)
*   **Manual Reality Check List**: `GET /analysis/reality-check/{project_id}`
*   **Regenerate Check Queries**: `POST /analysis/reality-check/{project_id}/generate`
*   **Save Reality Verification**: `PUT /analysis/reality-check/{project_id}/verify/{check_id}`
    *   *Body*: `{ "chatgpt_mentions": "YES", "gemini_mentions": "NO", "perplexity_mentions": "PARTIAL" }`
*   **Pipeline Health Metrics**: `GET /analysis/reliability/{project_id}`

### 3.7. Pipeline Execution Control (`analysis_execution.py`)
*   **Trigger New Audit Run**: `POST /analysis/run/{project_id}`
    *   *Status Code*: `202 Accepted`
*   **Check Audit Status**: `GET /analysis/status/{run_id}`
*   **External Service Dependencies Status**: `GET /analysis/dependencies`
*   **Resume Pipeline Run**: `POST /analysis/resume/{run_id}`
*   **Autonomous Tasks Queue**: `GET /analysis/execution/tasks/{project_id}`

### 3.8. Optimization Roadmap (`analysis_optimization.py`)
*   **Retrieve Recommendations Roadmap**: `GET /analysis/optimization-plan/{project_id}`
*   **Accept Action Item**: `POST /analysis/optimization-history/{project_id}`
    *   *Body*: `{ "recommendation": "Fix semantic structure on index", "status": "executed" }`
