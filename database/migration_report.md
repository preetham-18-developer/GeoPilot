# Database Schema Audit & Migration Report

## 1. Introduction

This audit report reconciles the local database schema definition (`database/schema.sql`) against the active live Supabase database instance (project `wnjnebqwgrjfsmbkgiua`). 

Ensuring alignment is critical to ensure local dev/testing correctness, API integrity, and to avoid runtime crashes from missing fields.

---

## 2. Findings

### 2.1. Missing Tables in `schema.sql`
Eight active tables exist in the live Supabase instance and are written to by the backend code (`app/agents/graph.py`), but were completely missing from the local `schema.sql` definition:
1. `blogs`
2. `competitor_feature_matrix`
3. `gap_analysis`
4. `extraction_failures`
5. `recommendation_simulations`
6. `entity_nodes`
7. `entity_relationships`
8. `content_coverage`

### 2.2. Missing Columns in `schema.sql`
Several table definitions inside `schema.sql` lagged behind the live Supabase database and the backend schemas. The following columns were missing locally:
* **`projects`**:
  - `current_agent` (text) — Tracks the active LangGraph stage.
* **`analysis_runs`**:
  - `current_agent` (text) — Tracks progress state.
* **`business_profiles`**:
  - `trust_signals` (text[]) — Verified certifications or ratings.
  - `business_model` (text) — E.g., SaaS, Subscription, etc.
  - `ai_visibility_opportunities` (text[]) — AI search recommendations.
* **`competitors`**:
  - `description` (text) — Profile overview.
  - `unique_features` (text[]) — Features the competitor has that the client does not.
  - `content_gaps` (text[]) — Over-performing content topics.
  - `reason_selected` (text[]) — Rationale for competitor choice.
  - `similarity_score` (integer) — Similarity index.
  - `industry_match` (text) — industry similarity detail.
  - `audience_match` (text) — target audience similarity detail.
  - `service_match` (text) — service parity detail.
  - `differentiation_score` (integer) — New column required for deterministic differentiation.
* **`content_opportunities`**:
  - `impact_score` (integer) — Impact rating.
  - `effort_score` (integer) — Implementation complexity.
  - `supporting_evidence` (text) — Verbatim backing fact.
  - `related_keywords` (text[]) — Keywords targeted.
  - `related_questions` (text[]) — Questions targeted.
  - `expected_benefit` (text) — Benefit detail.
* **`questions`**:
  - `coverage_score` (double precision) — New column required for deterministic coverage metrics.
  - `business_alignment` (double precision) — New column required for deterministic alignment metrics.

### 2.3. Dead/Unused Tables
The live Supabase database contains 6 tables which belong to a legacy project and are completely unused by GeoPilot:
* `colleges`
* `course_fees`
* `placement_stats`
* `admission_cutoffs`
* `reviews`
* `shortlist_sessions`

> [!CAUTION]
> **CRITICAL SECURITY RISK**:
> Row Level Security (RLS) is disabled on all 6 of these legacy tables. This means anyone with the anonymous key can read, modify, or delete rows in these tables.
> We recommend **dropping** these tables from Supabase completely to remove this security risk.

---

## 3. Remediation Plan

1. **Update `schema.sql`**: Inject all missing tables, columns, indexes, and RLS policies into the local source of truth schema file.
2. **Apply Supabase Migration**: Run SQL queries to apply column additions, create missing tables, enable RLS policies, and drop dead legacy tables.
