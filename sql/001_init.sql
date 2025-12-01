-- Enable UUID generator
create extension if not exists "pgcrypto";

-- Projects
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  status text not null default 'created' check (status in ('created','processing','ready','failed')),
  consolidated_payload jsonb,
  output_xlsx_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Documents
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  doc_type text not null,
  storage_path text not null,
  original_filename text not null,
  extracted_payload jsonb,
  status text not null default 'created',
  error text,
  created_at timestamptz not null default now()
);

create index if not exists idx_documents_project_id on public.documents(project_id);

-- Jobs
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  status text not null default 'created' check (status in ('created','processing','ready','failed')),
  logs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_jobs_project_id on public.jobs(project_id);

-- updated_at trigger
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists trg_projects_updated_at on public.projects;
create trigger trg_projects_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

drop trigger if exists trg_jobs_updated_at on public.jobs;
create trigger trg_jobs_updated_at
before update on public.jobs
for each row execute function public.set_updated_at();
