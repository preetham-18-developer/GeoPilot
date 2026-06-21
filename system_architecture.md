# System Architecture Document: AI Visibility Optimization SaaS Platform (AIVOP)

## Architecture Philosophy
This project is backend-first. The primary objective is to create a highly reliable, trace-accurate, and scalable AI-powered business intelligence platform. The platform prioritizes:
1. **Accuracy**: Strict prevention of hallucinations.
2. **Verification**: Explicit correlation of extracted facts with source URLs and evidence text.
3. **Scalability**: Decoupled crawler, agent networks, and transactional structures.
4. **Extensibility**: Swappable LLM layers, model switches, and standalone agent nodes.
5. **Traceability**: Audit logs and verified confidence scoring.

Frontend interfaces remain clean, simple, and professional—focusing on presenting raw, verified intelligence packages rather than styling/animations.

---

## High Level Data Flow

```
Customer
   │
   ▼
Next.js Frontend (App Router, TS, Vanilla CSS)
   │
   ▼
FastAPI Backend (REST API, JWT, CORS)
   │
   ▼
Agent Orchestrator (LangGraph state engine)
   │
   ├─► Crawler Agent
   ├─► Extraction Agent
   ├─► Verification Agent
   ├─► Business Intelligence Agent
   ├─► Question Discovery Agent
   ├─► Keyword Intelligence Agent
   ├─► Competitor Agent
   └─► Content Agent
   │
   ▼
Storage Layer
   │
   ├─► Supabase PostgreSQL (Structured data, profiles, and logs)
   ├─► Qdrant (In-memory/file-based local vector store)
   └─► Supabase Storage (Report exports and static PDFs)
```

---

## Frontend Architecture
- **Framework**: Next.js (App Router, React Server Components, TypeScript).
- **Styling**: Premium, responsive dark-theme styling using Vanilla CSS (`globals.css`).
- **Target Screens**:
  - **Landing Page**: Product introduction and CTA.
  - **Authentication**: Supabase Auth integration (Sign Up, Login, Forgot Password).
  - **Dashboard**: Project history, statistics, and core indicators.
  - **Projects / Project Details**: Control center containing:
    - Business Intelligence Summary & SWOT analysis
    - Factual Intelligence Tab (Verified facts, confidence scores, evidence snippets, source links)
    - FAQ Tab (Awareness, Consideration, decision, purchase, conversational questions with optimized answers)
    - Keywords Strategy Tab (Clustered intents, Themes)
    - Competitor Strategy Tab (Strengths, Weaknesses, market gaps)
    - Reports Export panel
  - **Settings & Config**: Key management and active profiles.
  - **Admin Screen**: System usage statistics and overview.

---

## Backend Architecture
- **Framework**: FastAPI.
- **Key Modules**:
  - `auth`: Dependency validation verifying Supabase JWTs.
  - `projects`: REST endpoints handling project creation and CAS (cascade delete) tracking.
  - `crawler`: Asynchronous BeautifulSoup4 recursive spider crawling up to 30 pages with in-memory hashing deduplication.
  - `agents`: Modular nodes controlled by a stateful LangGraph mapping fact parsing, strict evidence verifications, SWOT/GEO analyses, and keyword/competitor clustering.
  - `reports`: S3/Supabase Storage link loaders compiling Markdown exports.

---

## Agent Pipeline & Node Specification

1. **Crawler Agent**: Recursively discovers internal links and parses raw body contents, tags, and Structured Metadata into markdown text files, indexing chunks into local Qdrant collections.
2. **Extraction Agent**: Feeds text contexts to LLMs, parsing raw JSON parameters mapping company names, features, services, pricing, credentials, and testimonials.
3. **Verification Agent**: Audits raw extracted facts. Any fact unsupported by page context is rejected (`NOT FOUND`). Matches valid claims to exact verbatim evidence.
4. **Business Intelligence Agent**: Identifies the category/industry of the company, compiling strengths, SWOT matrices, and GEO gap reports.
5. **Question Discovery Agent**: Creates hundreds of realistic search engine inquiries categorized by intent (awareness, recommendation, purchase) with optimized answering templates.
6. **Keyword Agent**: Evaluates short/long-tail and conversational terms, clustering keywords by themes and user intents.
7. **Competitor Agent**: Profiles direct and indirect competitor matrices, gaps, and differentiation paths.
8. **Content Agent**: Recommends validated content/blog outlines using only verified facts.

---

## Database Schema Design (Supabase PostgreSQL)
All database tables have Row-Level Security (RLS) enabled to ensure multi-tenancy:
- `users`: User profiles.
- `projects`: Customer-defined websites and metadata.
- `websites` & `pages`: Crawler status, page HTML, markdown contents, and metadata.
- `analysis_runs`: Run status, times, and errors.
- `extracted_facts` & `verified_facts`: Structured fact details, evidence, confidence, and source links.
- `questions`, `keywords`, `competitors`, `reports`: Decoupled outputs from agent nodes.
- `activity_logs`: Audit logs tracing action details.
