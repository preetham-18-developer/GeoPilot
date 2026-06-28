# 🗄️ GeoPilot / AIVOP Database Documentation

This document describes the Supabase PostgreSQL database schemas, indexing structures, and Row-Level Security (RLS) configuration details for **GeoPilot**.

---

## 1. Schema Overview

GeoPilot utilizes a multi-tenant relational schema on Supabase PostgreSQL. Multi-tenancy is enforced natively via database Row-Level Security (RLS) matching authenticated user IDs.

---

## 2. Table Definitions

### 2.1. System & Workspace Management

#### `users`
*   **Description**: Stores tenant user accounts.
*   **Columns**:
    *   `id` (`uuid`, Primary Key): Matches Supabase Auth user ID.
    *   `email` (`text`, Unique): User contact email.
    *   `full_name` (`text`): User full name.
    *   `company_name` (`text`): Associated business name.
    *   `role` (`text`): Defaults to `customer`.
    *   `subscription_plan` (`text`): Defaults to `free`.
    *   `created_at` (`timestamp with time zone`): Record creation time.

#### `projects`
*   **Description**: Contains websites monitored by users.
*   **Columns**:
    *   `id` (`uuid`, Primary Key): Project identifier.
    *   `user_id` (`uuid`, Foreign Key -> `users.id`): Owner workspace user.
    *   `project_name` (`text`): Project label.
    *   `website_url` (`text`): URL to crawl and audit.
    *   `status` (`text`): Active crawling stage (e.g. `idle`, `queued`, `crawling`, `completed`, `failed`).
    *   `industry` (`text`): Detected business vertical.
    *   `current_agent` (`text`): Live agent executing the audit.
    *   `created_at` (`timestamp with time zone`)

---

### 2.2. Web Crawler & Scraping

#### `websites`
*   **Description**: Tracks crawling configurations.
*   **Columns**:
    *   `id` (`uuid`, Primary Key)
    *   `project_id` (`uuid`, Foreign Key -> `projects.id`)
    *   `domain` (`text`): Extracted target domain.
    *   `last_crawled_at` (`timestamp with time zone`)

#### `web_pages`
*   **Description**: Verbatim text contexts scraped from crawling.
*   **Columns**:
    *   `id` (`uuid`, Primary Key)
    *   `project_id` (`uuid`, Foreign Key -> `projects.id`)
    *   `url` (`text`): Page URL.
    *   `title` (`text`): HTML header title.
    *   `markdown_content` (`text`): Cleaned body copy in markdown format.
    *   `metadata` (`jsonb`): OpenGraph tags, schemas.
    *   `scraped_at` (`timestamp with time zone`)

---

### 2.3. Agent Intelligence & Optimization Outputs

#### `extracted_facts`
*   **Description**: Raw factual claims extracted by the Extraction Agent.
*   **Columns**:
    *   `id` (`uuid`, Primary Key)
    *   `project_id` (`uuid`, Foreign Key -> `projects.id`)
    *   `fact_category` (`text`): E.g., `services`, `credentials`, `pricing`.
    *   `fact_key` (`text`)
    *   `fact_value` (`text`)
    *   `evidence_text` (`text`): Backing context.
    *   `source_url` (`text`)
    *   `extracted_at` (`timestamp with time zone`)

#### `verified_facts`
*   **Description**: Claims audited and verified by the Verification Agent.
*   **Columns**:
    *   `id` (`uuid`, Primary Key)
    *   `extracted_fact_id` (`uuid`, Foreign Key -> `extracted_facts.id`): Direct audit link.
    *   `is_verified` (`boolean`): True if matching page text exists.
    *   `verification_score` (`numeric`): 0.0 - 100.0 confidence rating.
    *   `audit_log` (`text`): Reason for approval/rejection.
    *   `verified_at` (`timestamp with time zone`)

#### `questions`
*   **Description**: Discovered user queries grouped by search intent.
*   **Columns**:
    *   `id` (`uuid`, Primary Key)
    *   `project_id` (`uuid`, Foreign Key -> `projects.id`)
    *   `question_text` (`text`): Query format.
    *   `question_type` (`text`): E.g., `awareness`, `consideration`, `conversational`.
    *   `priority_score` (`integer`): Priority mapping.
    *   `optimized_answer` (`text`): LLM optimized context blueprint.
    *   `created_at` (`timestamp with time zone`)

#### `keywords`
*   **Description**: Target search terms.
*   **Columns**:
    *   `id` (`uuid`, Primary Key)
    *   `project_id` (`uuid`, Foreign Key -> `projects.id`)
    *   `keyword` (`text`)
    *   `keyword_type` (`text`): E.g., `brand`, `competitor`, `informational`.
    *   `search_volume` (`integer`): Estimated search count.
    *   `difficulty_score` (`integer`): Search competition rating.
    *   `created_at` (`timestamp with time zone`)

#### `competitors`
*   **Description**: Identified industry competitor matrices.
*   **Columns**:
    *   `id` (`uuid`, Primary Key)
    *   `project_id` (`uuid`, Foreign Key -> `projects.id`)
    *   `competitor_name` (`text`)
    *   `website` (`text`)
    *   `strengths` (`text[]`)
    *   `weaknesses` (`text[]`)
    *   `created_at` (`timestamp with time zone`)

---

## 3. Row-Level Security (RLS) Policies

Supabase enforces strict Row-Level Security (RLS) to ensure that users can only access their own data. Policies are applied as follows:

1.  **`users` Table**:
    *   Users can read and update only their own profile record.
    *   `auth.uid() = id`
2.  **`projects` Table**:
    *   Users can read, update, or delete only projects belonging to them.
    *   `auth.uid() = user_id`
3.  **Child Tables (`web_pages`, `extracted_facts`, `questions`, etc.)**:
    *   Access is gated by referencing the parent project's owner.
    *   `project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())`
