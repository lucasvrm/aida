-- Adiciona coluna opcional para armazenar o webhook de notificação de projetos
alter table public.aida_projects
    add column if not exists aida_webhook_url text;
