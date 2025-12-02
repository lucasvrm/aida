-- 1. Habilitar extensão para UUID (caso ainda não esteja habilitada)
create extension if not exists "pgcrypto";

-- ==============================================================================
-- TABELA: aida_projects
-- Armazena os projetos de extração (o "pai" de tudo)
-- ==============================================================================
create table if not exists public.aida_projects (
  aida_id uuid primary key default gen_random_uuid(),
  aida_name text not null,
  aida_status text not null default 'created' check (aida_status in ('created','processing','ready','failed')),
  aida_consolidated_payload jsonb,
  aida_output_xlsx_path text,
  aida_created_at timestamptz not null default now(),
  aida_updated_at timestamptz not null default now()
);

-- Habilitar RLS
alter table public.aida_projects enable row level security;

-- Política de Segurança:
-- Como o acesso é feito via API Python (usando a Service Role Key),
-- a Service Role já tem acesso total e ignora o RLS.
-- Bloqueamos acesso direto (anon/authenticated) por padrão para segurança.
create policy "Acesso total via Service Role"
  on public.aida_projects
  for all
  using ( auth.role() = 'service_role' );


-- ==============================================================================
-- TABELA: aida_documents
-- Armazena os arquivos (PDFs, Excel) vinculados a um projeto
-- ==============================================================================
create table if not exists public.aida_documents (
  aida_id uuid primary key default gen_random_uuid(),
  aida_project_id uuid not null references public.aida_projects(aida_id) on delete cascade,
  aida_doc_type text not null,
  aida_storage_path text not null,
  aida_original_filename text not null,
  aida_extracted_payload jsonb,
  aida_status text not null default 'created' check (aida_status in ('created','processing','ready','failed')),
  aida_error text,
  aida_created_at timestamptz not null default now(),
  aida_updated_at timestamptz not null default now()
);

create index if not exists idx_aida_documents_project_id on public.aida_documents(aida_project_id);

-- Habilitar RLS
alter table public.aida_documents enable row level security;

create policy "Acesso total via Service Role"
  on public.aida_documents
  for all
  using ( auth.role() = 'service_role' );


-- ==============================================================================
-- TABELA: aida_jobs
-- Armazena o status de processamento e logs do backend Python
-- ==============================================================================
create table if not exists public.aida_jobs (
  aida_id uuid primary key default gen_random_uuid(),
  aida_project_id uuid not null references public.aida_projects(aida_id) on delete cascade,
  aida_status text not null default 'created' check (aida_status in ('created','processing','ready','failed')),
  aida_run_number int not null default 1,
  aida_logs jsonb not null default '[]'::jsonb,
  aida_created_at timestamptz not null default now(),
  aida_updated_at timestamptz not null default now()
);

create index if not exists idx_aida_jobs_project_id on public.aida_jobs(aida_project_id);

-- Habilitar RLS
alter table public.aida_jobs enable row level security;

create policy "Acesso total via Service Role"
  on public.aida_jobs
  for all
  using ( auth.role() = 'service_role' );


-- ==============================================================================
-- TRIGGERS E FUNÇÕES
-- Atualiza automaticamente o campo aida_updated_at
-- ==============================================================================
create or replace function public.aida_set_updated_at()
returns trigger language plpgsql as $$
begin
  new.aida_updated_at = now();
  return new;
end $$;

-- Trigger para aida_projects
drop trigger if exists trg_aida_projects_updated_at on public.aida_projects;
create trigger trg_aida_projects_updated_at
before update on public.aida_projects
for each row execute function public.aida_set_updated_at();

-- Trigger para aida_documents
drop trigger if exists trg_aida_documents_updated_at on public.aida_documents;
create trigger trg_aida_documents_updated_at
before update on public.aida_documents
for each row execute function public.aida_set_updated_at();

-- Trigger para aida_jobs
drop trigger if exists trg_aida_jobs_updated_at on public.aida_jobs;
create trigger trg_aida_jobs_updated_at
before update on public.aida_jobs
for each row execute function public.aida_set_updated_at();
