-- Enable necessary extensions
create extension if not exists "uuid-ossp";

-- 1. USERS PROFILE (synced with Supabase Auth)
create table if not exists public.users (
  id uuid references auth.users on delete cascade primary key,
  email text not null,
  full_name text,
  company_name text,
  role text,
  subscription_plan text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. PROJECTS (Each analyzed website)
create table if not exists public.projects (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) on delete cascade not null,
  project_name text not null,
  website_url text not null,
  industry text,
  status text default 'pending' not null, -- 'pending', 'crawling', 'completed', 'failed'
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. ANALYSIS RUNS (Lifecycle tracking)
create table if not exists public.analysis_runs (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  run_type text default 'full' not null, -- 'full' or custom
  status text default 'pending' not null, -- 'pending', 'crawling', 'extracting', 'verifying', 'analyzing', 'completed', 'failed'
  started_at timestamp with time zone default timezone('utc'::text, now()) not null,
  completed_at timestamp with time zone,
  processing_time float, -- in seconds
  tokens_used integer default 0,
  error_message text
);

-- 4. WEB PAGES (Crawled pages)
create table if not exists public.web_pages (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  url text not null,
  title text,
  meta_description text,
  page_type text,
  content text,
  crawl_date timestamp with time zone default timezone('utc'::text, now()) not null,
  word_count integer,
  language text,
  status_code integer,
  hash text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 5. EXTRACTED FACTS (Raw facts before verification)
create table if not exists public.extracted_facts (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  page_id uuid references public.web_pages(id) on delete cascade,
  fact_category text not null,
  fact_key text not null,
  fact_value text not null,
  source_url text not null,
  evidence_text text,
  confidence_score float,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 6. VERIFIED FACTS (Audited facts with high confidence)
create table if not exists public.verified_facts (
  id uuid default gen_random_uuid() primary key,
  extracted_fact_id uuid references public.extracted_facts(id) on delete cascade not null,
  verification_status text not null, -- 'verified', 'rejected'
  verification_score float not null, -- score 0-100
  verified_by text not null, -- 'Verification Agent'
  verified_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 7. BUSINESS PROFILES (SWOT & Brand intelligence)
create table if not exists public.business_profiles (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  company_name text,
  industry text,
  description text,
  mission text,
  vision text,
  usp text,
  target_audience text,
  strengths text[],
  weaknesses text[],
  opportunities text[],
  risks text[],
  generated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 8. QUESTIONS (LLM / FAQ query generation)
create table if not exists public.questions (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  question text not null,
  question_type text not null, -- 'Awareness', 'Research', 'Comparison', 'Purchase', 'Recommendation', 'Conversational', 'AI Search'
  intent text,
  confidence_score float,
  recommended_answer text, -- Preserved for FAQ answer representation
  recommendation_score float,
  commercial_score float,
  intent_score float,
  priority_score float,
  difficulty_estimate text,
  opportunity_estimate text,
  priority text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 9. KEYWORDS (Semantic cluster keywords)
create table if not exists public.keywords (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  keyword text not null,
  keyword_type text not null, -- 'Short Tail', 'Long Tail', 'Semantic', 'Conversational', 'AI Search'
  intent text,
  cluster text,
  confidence_score float,
  priority text,
  difficulty_estimate text,
  opportunity_estimate text,
  source text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 10. COMPETITORS (Discovery results)
create table if not exists public.competitors (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  competitor_name text not null,
  website text,
  competitor_type text not null, -- 'direct', 'indirect'
  strengths text[],
  weaknesses text[],
  confidence_score float,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 11. CONTENT OPPORTUNITIES (Recommendations)
create table if not exists public.content_opportunities (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  title text not null,
  content_type text not null, -- 'Blog', 'Landing Page', 'FAQ Page', 'Guide', 'Comparison Page', 'Case Study', 'Knowledge Base'
  priority text not null, -- 'high', 'medium', 'low'
  reason text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 12. REPORTS (Compiled report details)
create table if not exists public.reports (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  report_type text not null,
  report_title text not null,
  report_content jsonb not null,
  generated_by text,
  generated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 13. AGENT RUNS (Token & execution time tracking)
create table if not exists public.agent_runs (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  agent_name text not null, -- 'Crawler', 'Extraction', 'Verification', etc.
  status text not null,
  input_tokens integer default 0,
  output_tokens integer default 0,
  processing_time float,
  error_message text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 14. ACTIVITY LOGS (Audit trail)
create table if not exists public.activity_logs (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) on delete cascade not null,
  project_id uuid references public.projects(id) on delete cascade,
  action text not null,
  metadata jsonb,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 15. NOTIFICATIONS
create table if not exists public.notifications (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) on delete cascade not null,
  title text not null,
  message text,
  status text default 'unread' not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 16. SUBSCRIPTIONS (Billing tier state)
create table if not exists public.subscriptions (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) on delete cascade not null,
  plan text not null,
  status text not null,
  renewal_date timestamp with time zone,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 17. QUALITY ASSURANCE REPORTS
create table if not exists public.qa_reports (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  run_id uuid references public.analysis_runs(id) on delete cascade not null,
  approval_status text not null,
  qa_score float not null,
  checks jsonb not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- FUTURE EXPANSION TABLES
create table if not exists public.ai_visibility_tracking (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  score float,
  details jsonb,
  tracked_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.search_queries (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  query_text text not null,
  volume integer default 0,
  click_through_rate float,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.recommendation_monitoring (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  platform text not null,
  recommendation_status text,
  monitored_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.content_performance (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  page_url text not null,
  views integer default 0,
  conversions integer default 0,
  recorded_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.competitor_tracking (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  competitor_id uuid references public.competitors(id) on delete cascade not null,
  visibility_score float,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.customer_feedback (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) on delete cascade not null,
  project_id uuid references public.projects(id) on delete cascade,
  feedback_text text not null,
  rating integer,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS & SECURITY TRIGGERS FOR MULTI-TENANCY
alter table public.users enable row level security;
alter table public.projects enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.web_pages enable row level security;
alter table public.extracted_facts enable row level security;
alter table public.verified_facts enable row level security;
alter table public.business_profiles enable row level security;
alter table public.questions enable row level security;
alter table public.keywords enable row level security;
alter table public.competitors enable row level security;
alter table public.content_opportunities enable row level security;
alter table public.reports enable row level security;
alter table public.agent_runs enable row level security;
alter table public.activity_logs enable row level security;
alter table public.notifications enable row level security;
alter table public.subscriptions enable row level security;
alter table public.ai_visibility_tracking enable row level security;
alter table public.search_queries enable row level security;
alter table public.recommendation_monitoring enable row level security;
alter table public.content_performance enable row level security;
alter table public.competitor_tracking enable row level security;
alter table public.customer_feedback enable row level security;
alter table public.qa_reports enable row level security;

-- Policies for isolated customer access
drop policy if exists "Users can view their own profile" on public.users;
create policy "Users can view their own profile" on public.users
  for all using (auth.uid() = id);

drop policy if exists "Users can view their own projects" on public.projects;
create policy "Users can view their own projects" on public.projects
  for all using (auth.uid() = user_id);

drop policy if exists "Users can view their own web pages" on public.web_pages;
create policy "Users can view their own web pages" on public.web_pages
  for all using (exists (
    select 1 from public.projects 
    where projects.id = web_pages.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own analysis runs" on public.analysis_runs;
create policy "Users can view their own analysis runs" on public.analysis_runs
  for all using (exists (
    select 1 from public.projects 
    where projects.id = analysis_runs.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own extracted facts" on public.extracted_facts;
create policy "Users can view their own extracted facts" on public.extracted_facts
  for all using (exists (
    select 1 from public.projects 
    where projects.id = extracted_facts.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own verified facts" on public.verified_facts;
create policy "Users can view their own verified facts" on public.verified_facts
  for all using (exists (
    select 1 from public.extracted_facts 
    join public.projects on projects.id = extracted_facts.project_id 
    where extracted_facts.id = verified_facts.extracted_fact_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own business profiles" on public.business_profiles;
create policy "Users can view their own business profiles" on public.business_profiles
  for all using (exists (
    select 1 from public.projects 
    where projects.id = business_profiles.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own questions" on public.questions;
create policy "Users can view their own questions" on public.questions
  for all using (exists (
    select 1 from public.projects 
    where projects.id = questions.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own keywords" on public.keywords;
create policy "Users can view their own keywords" on public.keywords
  for all using (exists (
    select 1 from public.projects 
    where projects.id = keywords.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own competitors" on public.competitors;
create policy "Users can view their own competitors" on public.competitors
  for all using (exists (
    select 1 from public.projects 
    where projects.id = competitors.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own content opportunities" on public.content_opportunities;
create policy "Users can view their own content opportunities" on public.content_opportunities
  for all using (exists (
    select 1 from public.projects 
    where projects.id = content_opportunities.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own reports" on public.reports;
create policy "Users can view their own reports" on public.reports
  for all using (exists (
    select 1 from public.projects 
    where projects.id = reports.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own agent runs" on public.agent_runs;
create policy "Users can view their own agent runs" on public.agent_runs
  for all using (exists (
    select 1 from public.projects 
    where projects.id = agent_runs.project_id and projects.user_id = auth.uid()
  ));

drop policy if exists "Users can view their own notifications" on public.notifications;
create policy "Users can view their own notifications" on public.notifications
  for all using (auth.uid() = user_id);

drop policy if exists "Users can view their own subscriptions" on public.subscriptions;
create policy "Users can view their own subscriptions" on public.subscriptions
  for all using (auth.uid() = user_id);

drop policy if exists "Users can view their own activity logs" on public.activity_logs;
create policy "Users can view their own activity logs" on public.activity_logs
  for all using (
    auth.uid() = user_id or 
    exists (select 1 from public.projects where projects.id = project_id and projects.user_id = auth.uid())
  );

drop policy if exists "Users can view their own QA reports" on public.qa_reports;
create policy "Users can view their own QA reports" on public.qa_reports
  for all using (exists (
    select 1 from public.projects 
    where projects.id = qa_reports.project_id and projects.user_id = auth.uid()
  ));

-- High-performance database indexes
create index if not exists idx_projects_user_id on public.projects(user_id);
create index if not exists idx_projects_website_url on public.projects(website_url);
create index if not exists idx_web_pages_project_id on public.web_pages(project_id);
create index if not exists idx_web_pages_url on public.web_pages(url);
create index if not exists idx_extracted_facts_project_id on public.extracted_facts(project_id);
create index if not exists idx_extracted_facts_page_id on public.extracted_facts(page_id);
create index if not exists idx_verified_facts_extracted_fact_id on public.verified_facts(extracted_fact_id);
create index if not exists idx_questions_project_id on public.questions(project_id);
create index if not exists idx_questions_question_type on public.questions(question_type);
create index if not exists idx_keywords_project_id on public.keywords(project_id);
create index if not exists idx_keywords_keyword_type on public.keywords(keyword_type);
create index if not exists idx_competitors_project_id on public.competitors(project_id);
create index if not exists idx_content_opportunities_project_id on public.content_opportunities(project_id);
create index if not exists idx_reports_project_id on public.reports(project_id);
create index if not exists idx_agent_runs_project_id on public.agent_runs(project_id);
create index if not exists idx_activity_logs_project_id on public.activity_logs(project_id);
create index if not exists idx_activity_logs_user_id on public.activity_logs(user_id);
create index if not exists idx_notifications_user_id on public.notifications(user_id);
create index if not exists idx_subscriptions_user_id on public.subscriptions(user_id);
create index if not exists idx_qa_reports_project_id on public.qa_reports(project_id);

-- User trigger on auth user created
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.users (id, email, full_name, company_name, role, subscription_plan)
  values (
    new.id, 
    new.email, 
    coalesce(new.raw_user_meta_data->>'full_name', ''),
    coalesce(new.raw_user_meta_data->>'company_name', ''),
    coalesce(new.raw_user_meta_data->>'role', 'customer'),
    coalesce(new.raw_user_meta_data->>'subscription_plan', 'free')
  );
  return new;
end;
$$ language plpgsql security definer;

-- Recreate trigger if it doesn't exist
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Data retention policy procedure
create or replace function public.apply_data_retention_policy()
returns void as $$
begin
  -- 1. Purge raw web_pages older than 12 months (365 days)
  delete from public.web_pages
  where created_at < now() - interval '12 months';

  -- 2. Purge agent_runs older than 90 days
  delete from public.agent_runs
  where created_at < now() - interval '90 days';

  -- 3. Purge activity_logs older than 180 days
  delete from public.activity_logs
  where created_at < now() - interval '180 days';
end;
$$ language plpgsql security definer;
